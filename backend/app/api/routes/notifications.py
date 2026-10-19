from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user_id
from app.db.session import get_db
from app.schemas.notifications import NotificationPreferences
from app.services.notification_preferences_service import get_preferences, save_preferences


router = APIRouter(prefix="/api/notifications/preferences", tags=["Notifications"])


@router.get("", response_model=NotificationPreferences)
def read_notification_preferences(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    return get_preferences(db, user_id)


@router.put("", response_model=NotificationPreferences)
def update_notification_preferences(data: NotificationPreferences, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    return save_preferences(db, user_id, data)
