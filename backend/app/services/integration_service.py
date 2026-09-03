from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

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
            access_token=access_token,
            refresh_token=refresh_token,
            token_expiry=token_expiry,
            scopes=scopes,
        )

        db.add(integration)

    else:
        integration.provider_account_id = provider_account_id
        integration.access_token = access_token

        if refresh_token is not None:
            integration.refresh_token = refresh_token

        integration.token_expiry = token_expiry
        integration.scopes = scopes

    db.commit()
    db.refresh(integration)

    return integration