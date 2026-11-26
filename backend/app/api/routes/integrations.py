from datetime import datetime
import logging
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import settings

from app.core.rate_limit_dependencies import google_read_limiter, oauth_connect_limiter
from app.core.security import get_current_user_id
from app.db.session import get_db
from app.integrations.google.client import (
    exchange_google_code,
    get_google_user_info,
)
from app.integrations.google import reads
from app.integrations.google.token_storage import TokenStorageError
from app.integrations.google.oauth import (
    GOOGLE_OAUTH_SCOPES,
    build_google_authorization_url,
    oauth_state_store,
)
from app.services.integration_service import upsert_google_integration
from app.models.integration import Integration
from app.schemas.integration import GoogleIntegrationStatus


logger = logging.getLogger(__name__)


def require_google_configuration() -> None:
    if settings.environment == "test":
        return
    if not settings.integration_token_key.get_secret_value():
        raise HTTPException(503, "Google token encryption is unavailable.")
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(503, "Google integration is unavailable.")



router = APIRouter(
    prefix="/api/integrations",
    tags=["Integrations"],
)


@router.get("/google/status", response_model=GoogleIntegrationStatus)
def google_status(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    integration = db.scalar(select(Integration).where(Integration.user_id == user_id, Integration.provider == "google"))
    if integration is None:
        return {"status": "disconnected", "scopes": [], "last_sync_at": None}
    return {"status": "connected", "scopes": integration.scopes.split() if integration.scopes else [], "last_sync_at": integration.last_synced_at}


@router.delete("/google", status_code=status.HTTP_204_NO_CONTENT)
def disconnect_google(revoke_provider: bool = False, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    integration = db.scalar(select(Integration).where(Integration.user_id == user_id, Integration.provider == "google"))
    if integration is not None:
        if revoke_provider:
            try:
                reads.revoke(integration)
            except (reads.GoogleReadError, TokenStorageError):
                raise HTTPException(502, "Google revocation could not be confirmed.") from None
        db.delete(integration)
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/google/connect")
def connect_google(
    service: Literal["gmail", "calendar", "drive"] | None = None,
    user_id: int = Depends(get_current_user_id),
):
    require_google_configuration()
    if not oauth_connect_limiter.allow(str(user_id)):
        raise HTTPException(429, "Too many Google connection attempts.",
                            headers={"Retry-After": str(oauth_connect_limiter.window_seconds)})
    scope = {"gmail": "gmail.readonly", "calendar": "calendar.freebusy", "drive": "drive.readonly"}
    scopes = (*GOOGLE_OAUTH_SCOPES[:2], reads.SCOPE + scope[service]) if service else None
    try:
        state = oauth_state_store.create(user_id, scopes)
    except ValueError as exc:
        raise HTTPException(429, str(exc)) from None
    authorization_url = build_google_authorization_url(state, scopes)

    return {
        "authorization_url": authorization_url,
    }


@router.get("/google/callback")
def google_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None, max_length=128),
    error: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    if error:
        if state:
            oauth_state_store.consume_grant(state)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google authorization failed.",
        )

    if not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing OAuth state",
        )

    grant = oauth_state_store.consume_grant(state)

    if grant is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state",
        )

    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing authorization code",
        )

    user_id, requested_scopes = grant
    require_google_configuration()
    stage = "token_exchange"
    try:
        credentials = exchange_google_code(code, requested_scopes) if requested_scopes else exchange_google_code(code)
        stage = "scope_validation"
        granted_scopes = getattr(credentials, "granted_scopes", None)
        scopes = credentials.scopes if granted_scopes is None else granted_scopes
        allowed = requested_scopes or GOOGLE_OAUTH_SCOPES
        scopes = [GOOGLE_OAUTH_SCOPES[1] if scope == "email" else scope for scope in scopes or ()]
        if (not credentials.token or not set(scopes).issubset(allowed)
                or (requested_scopes and requested_scopes[-1] not in scopes)):
            raise ValueError
        stage = "account_lookup"
        google_user = get_google_user_info(credentials)
    except Exception as exc:
        provider_error = getattr(exc, "error", None)
        known_errors = ("invalid_client", "invalid_grant", "invalid_request", "invalid_scope",
                        "unauthorized_client", "access_denied", "unsupported_grant_type")
        logger.warning("Google OAuth callback failed: stage=%s error_type=%s provider_code=%s",
                       stage, type(exc).__name__, provider_error if provider_error in known_errors else "unavailable")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to complete Google OAuth",
        ) from None

    provider_account_id = google_user.get("id") if isinstance(google_user, dict) else None

    if not isinstance(provider_account_id, str) or not provider_account_id.strip() or len(provider_account_id) > 255:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Google account identity was not returned",
        )

    scopes_value = " ".join(scopes) if scopes else None

    upsert_google_integration(
        db=db,
        user_id=user_id,
        provider_account_id=provider_account_id,
        access_token=credentials.token,
        refresh_token=credentials.refresh_token,
        token_expiry=credentials.expiry,
        scopes=scopes_value,
    )

    return RedirectResponse(
        url=f"{settings.frontend_url.rstrip('/')}/settings?google=connected",
        status_code=303,
    )

class GoogleRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    authorized: StrictBool
    service: Literal["gmail", "drive", "calendar"]
    query: str = Field(default="", max_length=250)
    item_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]{1,128}$")
    page_token: str | None = Field(default=None, max_length=reads.MAX_PAGE_TOKEN_LENGTH)
    start_at: datetime | None = None
    end_at: datetime | None = None


@router.post("/google/read")
def read_google(body: GoogleRead, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    if not body.authorized:
        raise HTTPException(403, "Explicit Google read authorization is required.")
    if not google_read_limiter.allow(str(user_id)):
        raise HTTPException(429, "Too many Google reads. Try again later.",
                            headers={"Retry-After": str(google_read_limiter.window_seconds)})
    try:
        if body.service == "calendar":
            if body.start_at is None or body.end_at is None:
                raise ValueError("Calendar reads require a start and end.")
            result = {"busy": [{"start_at": start, "end_at": end}
                               for start, end in reads.free_busy(db, user_id, body.start_at, body.end_at)]}
        elif body.service == "gmail":
            result = reads.gmail(db, user_id, query=body.query, message_id=body.item_id, page_token=body.page_token)
        else:
            result = reads.drive(db, user_id, file_id=body.item_id, page_token=body.page_token)
        db.commit()
        return result
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from None
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    except reads.GoogleReadRateLimited as exc:
        raise HTTPException(429, str(exc)) from None
    except reads.GoogleReadError as exc:
        raise HTTPException(502, str(exc)) from None
