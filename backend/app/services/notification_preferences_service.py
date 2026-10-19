from sqlalchemy.orm import Session

from app.models.notification_preference import UserNotificationPreference
from app.schemas.notifications import NotificationPreferences


def get_preferences(db: Session, user_id: int) -> NotificationPreferences:
    preferences = db.get(UserNotificationPreference, user_id)
    return NotificationPreferences.model_validate(preferences or {"user_id": user_id})


def save_preferences(db: Session, user_id: int, data: NotificationPreferences) -> NotificationPreferences:
    preferences = db.get(UserNotificationPreference, user_id)
    if preferences is None:
        preferences = UserNotificationPreference(user_id=user_id, **data.model_dump())
        db.add(preferences)
    else:
        for field, value in data.model_dump().items():
            setattr(preferences, field, value)
    db.commit()
    db.refresh(preferences)
    return NotificationPreferences.model_validate(preferences)
