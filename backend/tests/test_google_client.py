from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from google.oauth2.credentials import Credentials
from sqlalchemy.orm import Session

from app.integrations.google.client import (
    GoogleAPIServiceError,
    build_calendar_service,
    build_drive_service,
    build_gmail_service,
    build_google_service,
)
from app.models.integration import Integration
from app.models.user import User
from tests.conftest import test_engine


def create_test_user(db: Session) -> User:
    user = User(
        email="google-client-test@example.com",
        password_hash="test-password-hash",
        name="Google Client Test User",
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def create_google_integration(
    db: Session,
    user_id: int,
) -> Integration:
    integration = Integration(
        user_id=user_id,
        provider="google",
        provider_account_id="google-client-test",
        access_token="access-token",
        refresh_token="refresh-token",
        token_expiry=(
            datetime.now(timezone.utc)
            + timedelta(hours=1)
        ),
        scopes=(
            "openid "
            "https://www.googleapis.com/auth/gmail.readonly "
            "https://www.googleapis.com/auth/calendar.readonly "
            "https://www.googleapis.com/auth/drive.readonly"
        ),
    )

    db.add(integration)
    db.commit()
    db.refresh(integration)

    return integration


@patch("app.integrations.google.client.build")
@patch(
    "app.integrations.google.client.get_user_google_credentials"
)
def test_build_google_service(
    mock_get_credentials,
    mock_build,
):
    credentials = MagicMock(spec=Credentials)
    service = MagicMock()

    mock_get_credentials.return_value = credentials
    mock_build.return_value = service

    with Session(test_engine) as db:
        result = build_google_service(
            db=db,
            user_id=1,
            service_name="gmail",
            version="v1",
        )

    assert result is service

    mock_get_credentials.assert_called_once_with(
        db=db,
        user_id=1,
    )

    mock_build.assert_called_once_with(
        "gmail",
        "v1",
        credentials=credentials,
        cache_discovery=False,
    )


@patch("app.integrations.google.client.build")
@patch(
    "app.integrations.google.client.get_user_google_credentials"
)
def test_build_google_service_wraps_credential_error(
    mock_get_credentials,
    mock_build,
):
    from app.integrations.google.credentials import (
        GoogleCredentialsError,
    )

    mock_get_credentials.side_effect = GoogleCredentialsError(
        "credential failure"
    )

    with Session(test_engine) as db:
        with pytest.raises(GoogleAPIServiceError):
            build_google_service(
                db=db,
                user_id=1,
                service_name="gmail",
                version="v1",
            )

    mock_build.assert_not_called()


@patch("app.integrations.google.client.build")
@patch(
    "app.integrations.google.client.get_user_google_credentials"
)
def test_build_google_service_wraps_build_error(
    mock_get_credentials,
    mock_build,
):
    credentials = MagicMock(spec=Credentials)

    mock_get_credentials.return_value = credentials
    mock_build.side_effect = RuntimeError("build failure")

    with Session(test_engine) as db:
        with pytest.raises(GoogleAPIServiceError):
            build_google_service(
                db=db,
                user_id=1,
                service_name="gmail",
                version="v1",
            )


@patch("app.integrations.google.client.build_google_service")
def test_build_gmail_service(mock_build_service):
    service = MagicMock()
    mock_build_service.return_value = service

    with Session(test_engine) as db:
        result = build_gmail_service(
            db=db,
            user_id=1,
        )

    assert result is service

    mock_build_service.assert_called_once_with(
        db=db,
        user_id=1,
        service_name="gmail",
        version="v1",
    )


@patch("app.integrations.google.client.build_google_service")
def test_build_calendar_service(mock_build_service):
    service = MagicMock()
    mock_build_service.return_value = service

    with Session(test_engine) as db:
        result = build_calendar_service(
            db=db,
            user_id=1,
        )

    assert result is service

    mock_build_service.assert_called_once_with(
        db=db,
        user_id=1,
        service_name="calendar",
        version="v3",
    )


@patch("app.integrations.google.client.build_google_service")
def test_build_drive_service(mock_build_service):
    service = MagicMock()
    mock_build_service.return_value = service

    with Session(test_engine) as db:
        result = build_drive_service(
            db=db,
            user_id=1,
        )

    assert result is service

    mock_build_service.assert_called_once_with(
        db=db,
        user_id=1,
        service_name="drive",
        version="v3",
    )