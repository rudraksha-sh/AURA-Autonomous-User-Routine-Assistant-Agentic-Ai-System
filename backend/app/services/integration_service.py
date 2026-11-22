from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.google.token_storage import protect_token
from app.models.integration import Integration


def get_google_integration(
    db: Session,
    user_id: int,
) -> Integration | None:
    return db.scalar(
        select(Integration).where(
            Integration.user_id == user_id,
            Integration.provider == "google",
        )
    )


def upsert_google_integration(
    db: Session,
    *,
    user_id: int,
    provider_account_id: str,
    access_token: str,
    refresh_token: str | None,
    token_expiry: datetime | None,
    scopes: str | None,
) -> Integration:
    integration = get_google_integration(
        db=db,
        user_id=user_id,
    )

    if integration is None:
        integration = Integration(
            user_id=user_id,
            provider="google",
            provider_account_id=provider_account_id,
            access_token=protect_token(access_token),
            refresh_token=protect_token(refresh_token),
            token_expiry=token_expiry,
            scopes=scopes,
        )

        db.add(integration)

    else:
        account_changed = integration.provider_account_id != provider_account_id
        integration.provider_account_id = provider_account_id
        integration.access_token = protect_token(access_token)

        if refresh_token is not None or account_changed:
            integration.refresh_token = protect_token(refresh_token)
        else:
            integration.refresh_token = protect_token(integration.refresh_token)
        if account_changed:
            integration.last_synced_at = None

        integration.token_expiry = token_expiry
        integration.scopes = scopes

    db.commit()
    db.refresh(integration)

    return integration