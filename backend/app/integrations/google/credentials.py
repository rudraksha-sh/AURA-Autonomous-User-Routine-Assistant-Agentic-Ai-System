from datetime import datetime, timezone

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.integration import Integration
from app.services.integration_service import get_google_integration


class GoogleCredentialsError(Exception):
    """Base exception for Google credential failures."""


class GoogleIntegrationNotFoundError(GoogleCredentialsError):
    """Raised when a user has no Google integration."""


class GoogleRefreshTokenMissingError(GoogleCredentialsError):
    """Raised when a Google integration has no refresh token."""


def build_google_credentials(
    integration: Integration,
) -> Credentials:
    """
    Build Google OAuth credentials from a stored integration.
    """

    if not integration.access_token:
        raise GoogleCredentialsError(
            "Google access token is missing"
        )

    return Credentials(
        token=integration.access_token,
        refresh_token=integration.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        scopes=(
            integration.scopes.split()
            if integration.scopes
            else None
        ),
    )


def is_token_expired(
    token_expiry: datetime | None,
) -> bool:
    """
    Determine whether the stored Google access token is expired.

    The database token_expiry value is treated as the source of truth.
    """

    if token_expiry is None:
        return True

    if token_expiry.tzinfo is None:
        token_expiry = token_expiry.replace(
            tzinfo=timezone.utc
        )

    return token_expiry <= datetime.now(timezone.utc)


def get_user_google_credentials(
    db: Session,
    user_id: int,
) -> Credentials:
    """
    Load the user's Google integration.

    If the stored access token is expired, refresh it using the
    stored refresh token and persist the new token information.
    """

    integration = get_google_integration(
        db=db,
        user_id=user_id,
    )

    if integration is None:
        raise GoogleIntegrationNotFoundError(
            "Google integration is not connected"
        )

    credentials = build_google_credentials(integration)

    if not is_token_expired(integration.token_expiry):
        return credentials

    if not integration.refresh_token:
        raise GoogleRefreshTokenMissingError(
            "Google refresh token is missing"
        )

    try:
        credentials.refresh(Request())
    except Exception as exc:
        raise GoogleCredentialsError(
            "Failed to refresh Google access token"
        ) from exc

    if not credentials.token:
        raise GoogleCredentialsError(
            "Google refresh returned no access token"
        )

    integration.access_token = credentials.token
    integration.token_expiry = credentials.expiry

    db.commit()
    db.refresh(integration)

    return credentials