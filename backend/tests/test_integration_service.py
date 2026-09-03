from datetime import datetime, timezone

from app.db.session import SessionLocal
from app.models.user import User
from app.services.integration_service import (
    get_google_integration,
    upsert_google_integration,
)


def create_test_user(db_session) -> User:
    user = User(
        email="integration-test@example.com",
        password_hash="test-password-hash",
        name="Integration Test User",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_google_integration_can_be_created():
    with SessionLocal() as db_session:
        user = create_test_user(db_session)

        integration = upsert_google_integration(
            db=db_session,
            user_id=user.id,
            provider_account_id="google-user-123",
            access_token="access-token",
            refresh_token="refresh-token",
            token_expiry=datetime.now(timezone.utc),
            scopes="openid email",
        )

        assert integration.id is not None
        assert integration.user_id == user.id
        assert integration.provider == "google"
        assert integration.provider_account_id == "google-user-123"


def test_google_integration_is_updated_instead_of_duplicated():
    with SessionLocal() as db_session:
        user = create_test_user(db_session)

        first = upsert_google_integration(
            db=db_session,
            user_id=user.id,
            provider_account_id="google-user-123",
            access_token="access-token-1",
            refresh_token="refresh-token-1",
            token_expiry=None,
            scopes="openid email",
        )

        second = upsert_google_integration(
            db=db_session,
            user_id=user.id,
            provider_account_id="google-user-123",
            access_token="access-token-2",
            refresh_token=None,
            token_expiry=None,
            scopes="openid email gmail.readonly",
        )

        assert second.id == first.id
        assert second.access_token == "access-token-2"
        assert second.refresh_token == "refresh-token-1"
        assert second.scopes == "openid email gmail.readonly"


def test_get_google_integration_returns_existing_record():
    with SessionLocal() as db_session:
        user = create_test_user(db_session)

        created = upsert_google_integration(
            db=db_session,
            user_id=user.id,
            provider_account_id="google-user-123",
            access_token="access-token",
            refresh_token="refresh-token",
            token_expiry=None,
            scopes="openid email",
        )

        result = get_google_integration(
            db=db_session,
            user_id=user.id,
        )

        assert result is not None
        assert result.id == created.id