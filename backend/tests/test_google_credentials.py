from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from google.oauth2.credentials import Credentials
from sqlalchemy.orm import Session

from app.integrations.google.credentials import (
    GoogleCredentialsError,
    GoogleIntegrationNotFoundError,
    GoogleRefreshTokenMissingError,
    build_google_credentials,
    get_user_google_credentials,
)
from app.models.integration import Integration
from app.models.user import User
from tests.conftest import test_engine


def create_test_user(db: Session) -> User:
    user = User(
        email="credentials-test@example.com",
        password_hash="test-password-hash",
        name="Credentials Test User",
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def test_build_google_credentials():
    integration = Integration(
        user_id=1,
        provider="google",
        provider_account_id="google-123",
        access_token="access-token",
        refresh_token="refresh-token",
        scopes=(
            "openid "
            "https://www.googleapis.com/auth/gmail.readonly"
        ),
    )

    credentials = build_google_credentials(integration)

    assert isinstance(credentials, Credentials)
    assert credentials.token == "access-token"
    assert credentials.refresh_token == "refresh-token"
    assert (
        credentials.token_uri
        == "https://oauth2.googleapis.com/token"
    )

    assert credentials.scopes == [
        "openid",
        "https://www.googleapis.com/auth/gmail.readonly",
    ]


def test_google_integration_not_found():
    with Session(test_engine) as db:
        with pytest.raises(GoogleIntegrationNotFoundError):
            get_user_google_credentials(
                db=db,
                user_id=999999,
            )


def test_refresh_token_missing():
    with Session(test_engine) as db:
        user = create_test_user(db)

        integration = Integration(
            user_id=user.id,
            provider="google",
            provider_account_id="google-123",
            access_token="access-token",
            refresh_token=None,
            token_expiry=(
                datetime.now(timezone.utc)
                - timedelta(minutes=5)
            ),
            scopes="openid",
        )

        db.add(integration)
        db.commit()

        with pytest.raises(GoogleRefreshTokenMissingError):
            get_user_google_credentials(
                db=db,
                user_id=user.id,
            )


@patch(
    "app.integrations.google.credentials.Credentials.refresh",
    autospec=True,
)
def test_expired_credentials_are_refreshed(
    mock_refresh,
):
    with Session(test_engine) as db:
        user = create_test_user(db)

        integration = Integration(
            user_id=user.id,
            provider="google",
            provider_account_id="google-123",
            access_token="old-access-token",
            refresh_token="refresh-token",
            token_expiry=(
                datetime.now(timezone.utc)
                - timedelta(minutes=5)
            ),
            scopes="openid",
        )

        db.add(integration)
        db.commit()
        db.refresh(integration)

        def refresh_credentials(credentials, request):
            credentials.token = "new-access-token"
            credentials.expiry = (
                datetime.now(timezone.utc)
                + timedelta(hours=1)
            )

        mock_refresh.side_effect = refresh_credentials

        credentials = get_user_google_credentials(
            db=db,
            user_id=user.id,
        )

        assert credentials.token == "new-access-token"

        db.refresh(integration)

        assert (
            integration.access_token
            == "new-access-token"
        )

        assert integration.token_expiry is not None

        mock_refresh.assert_called_once()


def test_valid_credentials_are_not_refreshed():
    with Session(test_engine) as db:
        user = create_test_user(db)

        integration = Integration(
            user_id=user.id,
            provider="google",
            provider_account_id="google-123",
            access_token="valid-access-token",
            refresh_token="refresh-token",
            token_expiry=(
                datetime.now(timezone.utc)
                + timedelta(hours=1)
            ),
            scopes="openid",
        )

        db.add(integration)
        db.commit()

        with patch(
            "app.integrations.google.credentials.Credentials.refresh"
        ) as mock_refresh:
            credentials = get_user_google_credentials(
                db=db,
                user_id=user.id,
            )

            assert (
                credentials.token
                == "valid-access-token"
            )

            mock_refresh.assert_not_called()