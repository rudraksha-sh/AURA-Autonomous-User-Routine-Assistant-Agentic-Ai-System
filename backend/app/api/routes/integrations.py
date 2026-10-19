from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import get_current_user_id
from app.db.session import get_db
from app.integrations.google.client import (
    exchange_google_code,
    get_google_user_info,
)
from app.integrations.google.oauth import (
    build_google_authorization_url,
    oauth_state_store,
)
from app.services.integration_service import upsert_google_integration
from app.models.integration import Integration
from app.schemas.integration import GoogleIntegrationStatus


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
def disconnect_google(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    integration = db.scalar(select(Integration).where(Integration.user_id == user_id, Integration.provider == "google"))
    if integration is not None:
        db.delete(integration)
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/google/connect")
def connect_google(
    user_id: int = Depends(get_current_user_id),
):
    state = oauth_state_store.create(user_id)

    authorization_url = build_google_authorization_url(state)

    return {
        "authorization_url": authorization_url,
    }


@router.get("/google/callback")
def google_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google authorization failed: {error}",
        )

    if not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing OAuth state",
        )

    user_id = oauth_state_store.consume(state)

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state",
        )

    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing authorization code",
        )

    try:
        credentials = exchange_google_code(code)
        google_user = get_google_user_info(credentials)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to complete Google OAuth",
        ) from exc

    provider_account_id = google_user.get("id")

    if not provider_account_id:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Google account identity was not returned",
        )

    scopes = credentials.scopes
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

    return {
        "status": "connected",
        "provider": "google",
        "provider_account_id": provider_account_id,
    }
