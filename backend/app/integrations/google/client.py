from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import Resource, build
from sqlalchemy.orm import Session

from app.core.config import settings
from app.integrations.google.credentials import (
    GoogleCredentialsError,
    get_user_google_credentials,
)
from app.integrations.google.oauth import GOOGLE_OAUTH_SCOPES


class GoogleAPIError(Exception):
    """Base exception for Google API client failures."""


class GoogleAPIServiceError(GoogleAPIError):
    """Raised when a Google API service cannot be created."""


def create_google_flow() -> Flow:
    """
    Create a Google OAuth flow using the application's Google credentials.
    """

    client_config = {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.google_redirect_uri],
        }
    }

    return Flow.from_client_config(
        client_config,
        scopes=GOOGLE_OAUTH_SCOPES,
        redirect_uri=settings.google_redirect_uri,
    )


def exchange_google_code(code: str):
    """
    Exchange a Google authorization code for OAuth credentials.
    """

    flow = create_google_flow()
    flow.fetch_token(code=code)

    return flow.credentials


def get_google_user_info(credentials):
    """
    Retrieve the Google account identity associated with credentials.
    """

    service = build(
        "oauth2",
        "v2",
        credentials=credentials,
        cache_discovery=False,
    )

    return service.userinfo().get().execute()


def build_google_service(
    db: Session,
    user_id: int,
    service_name: str,
    version: str,
) -> Resource:
    """
    Build an authenticated Google API service for a user.

    Credentials are loaded through the centralized Google credential
    lifecycle so expired access tokens are refreshed automatically.
    """

    try:
        credentials = get_user_google_credentials(
            db=db,
            user_id=user_id,
        )
    except GoogleCredentialsError as exc:
        raise GoogleAPIServiceError(
            "Unable to load Google credentials"
        ) from exc

    try:
        return build(
            service_name,
            version,
            credentials=credentials,
            cache_discovery=False,
        )
    except Exception as exc:
        raise GoogleAPIServiceError(
            f"Failed to build Google API service: {service_name}"
        ) from exc


def build_gmail_service(
    db: Session,
    user_id: int,
) -> Resource:
    """Build an authenticated Gmail API service."""

    return build_google_service(
        db=db,
        user_id=user_id,
        service_name="gmail",
        version="v1",
    )


def build_calendar_service(
    db: Session,
    user_id: int,
) -> Resource:
    """Build an authenticated Google Calendar API service."""

    return build_google_service(
        db=db,
        user_id=user_id,
        service_name="calendar",
        version="v3",
    )


def build_drive_service(
    db: Session,
    user_id: int,
) -> Resource:
    """Build an authenticated Google Drive API service."""

    return build_google_service(
        db=db,
        user_id=user_id,
        service_name="drive",
        version="v3",
    )
    