"""Explicit, bounded Google reads. Provider response bodies never enter workflow state."""
import json
from datetime import datetime, timedelta
from urllib.parse import quote

import httpx
from sqlalchemy.orm import Session

from app.integrations.google.credentials import GoogleCredentialsError, get_user_google_credentials
from app.integrations.google.oauth import GOOGLE_OAUTH_SCOPES
from app.integrations.google.token_storage import PREFIX, reveal_token
from app.services.integration_service import get_google_integration

SCOPE = "https://www.googleapis.com/auth/"
CALENDAR_SCOPES = ("calendar.freebusy", "calendar.readonly", "calendar.events.freebusy")
READ_SCOPES = frozenset((*GOOGLE_OAUTH_SCOPES, "email", *(SCOPE + scope for scope in CALENDAR_SCOPES)))
MAX_BYTES = 262_144
MAX_PAGE_TOKEN_LENGTH = 4096


class GoogleReadError(Exception):
    pass


class GoogleReadRateLimited(GoogleReadError):
    pass


def _request(method, url, token, *, params=None, body=None, as_text=False):
    try:
        with httpx.stream(method, url, headers={"Authorization": f"Bearer {token}"},
                          params=params, json=body, timeout=5, follow_redirects=False) as response:
            if response.status_code == 429:
                raise GoogleReadRateLimited("Google read rate limit reached. Try again later.")
            response.raise_for_status()
            data = bytearray()
            for chunk in response.iter_bytes(chunk_size=8192):
                data.extend(chunk)
                if len(data) > MAX_BYTES:
                    raise GoogleReadError("Google returned more data than the read limit.")
            if as_text:
                return data.decode("utf-8")[:16_000]
            payload = json.loads(data)
            if not isinstance(payload, dict):
                raise GoogleReadError("Google returned an invalid read response.")
            return payload
    except (httpx.HTTPError, ValueError):
        raise GoogleReadError("Google read unavailable. Reconnect if access was revoked.") from None


def require_read_grant(integration, scopes):
    granted = set((integration.scopes or "").split()) if integration is not None else set()
    if not granted.issubset(READ_SCOPES) or not granted.intersection(SCOPE + scope for scope in scopes):
        raise PermissionError("Connect Google with the required read permission.")
    if not (integration.access_token or "").startswith(PREFIX) or (
        integration.refresh_token and not integration.refresh_token.startswith(PREFIX)
    ):
        raise PermissionError("Reconnect Google to enable encrypted read access.")


def _token(db: Session, user_id: int, scopes: tuple[str, ...]) -> str:
    integration = get_google_integration(db, user_id)
    require_read_grant(integration, scopes)
    try:
        return get_user_google_credentials(db, user_id, commit=False).token
    except GoogleCredentialsError:
        raise GoogleReadError("Google credentials unavailable. Reconnect Google.") from None


def free_busy(db, user_id, start: datetime, end: datetime) -> list[tuple[datetime, datetime]]:
    if start.utcoffset() is None or end.utcoffset() is None or not timedelta(0) < end - start <= timedelta(days=7):
        raise ValueError("Provide a time-zoned interval of up to seven days.")
    token = _token(db, user_id, CALENDAR_SCOPES)
    data = _request("POST", "https://www.googleapis.com/calendar/v3/freeBusy", token,
                    body={"timeMin": start.isoformat(), "timeMax": end.isoformat(), "items": [{"id": "primary"}]})
    try:
        calendars = data["calendars"]
        if not isinstance(calendars, dict) or len(calendars) != 1 or data.get("groups"):
            raise ValueError
        calendar = next(iter(calendars.values()))
        blocks = calendar["busy"]
        if calendar.get("errors") or not isinstance(blocks, list) or len(blocks) > 250:
            raise ValueError
        result = []
        for block in blocks:
            left, right = (datetime.fromisoformat(block[key].replace("Z", "+00:00")) for key in ("start", "end"))
            if left.utcoffset() is None or right.utcoffset() is None or left >= right:
                raise ValueError
            if left < end and right > start:
                result.append((max(start, left), min(end, right)))
        return sorted(result)
    except (KeyError, TypeError, ValueError, AttributeError):
        raise GoogleReadError("Google returned invalid availability.") from None


def _page(data, key):
    items = data.get(key, [])
    token = data.get("nextPageToken")
    if (not isinstance(items, list) or len(items) > 20
            or any(not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"]
                   for item in items)
            or ("nextPageToken" in data and (not isinstance(token, str) or not 0 < len(token) <= MAX_PAGE_TOKEN_LENGTH))):
        raise GoogleReadError("Google returned an invalid page.")
    return data


def gmail(db, user_id, *, query="", message_id=None, page_token=None):
    token = _token(db, user_id, ("gmail.readonly",))
    url = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
    if message_id:
        message = _request("GET", f"{url}/{quote(message_id, safe='')}", token, params={"format": "full"})
        if message.get("id") != message_id or not isinstance(message.get("payload"), dict):
            raise GoogleReadError("Gmail returned an invalid message.")
        return message
    return _page(_request("GET", url, token, params={"q": query, "maxResults": 20, **(
        {"pageToken": page_token} if page_token else {})}), "messages")


def drive(db, user_id, *, file_id=None, page_token=None):
    token = _token(db, user_id, ("drive.readonly",))
    url = "https://www.googleapis.com/drive/v3/files"
    if file_id:
        url = f"{url}/{quote(file_id, safe='')}"
        metadata = _request("GET", url, token, params={"fields": "mimeType,trashed"})
        if metadata.get("trashed") is not False:
            raise GoogleReadError("Drive file is unavailable.")
        mime = metadata.get("mimeType")
        if mime == "application/vnd.google-apps.document":
            return {"text": _request("GET", f"{url}/export", token, params={"mimeType": "text/plain"}, as_text=True)}
        if mime in {"text/plain", "text/markdown"}:
            return {"text": _request("GET", url, token, params={"alt": "media"}, as_text=True)}
        raise GoogleReadError("Only Google Docs and plain text files are supported.")
    return _page(_request("GET", url, token, params={"q": "trashed = false", "pageSize": 20,
                    "fields": "nextPageToken,files(id,name,mimeType,modifiedTime),incompleteSearch", **(
                        {"pageToken": page_token} if page_token else {})}), "files")


def revoke(integration) -> None:
    token = reveal_token(integration.refresh_token or integration.access_token)
    if token:
        try:
            httpx.post("https://oauth2.googleapis.com/revoke", data={"token": token},
                       timeout=5, follow_redirects=False).raise_for_status()
        except httpx.HTTPError:
            raise GoogleReadError("Google revocation could not be confirmed.") from None
