from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.integrations.google.client import build_calendar_service
from app.schemas.calendar import CalendarBusyBlock, CalendarBusyResponse
from app.services.integration_service import get_google_integration
from app.services.daily_planner_service import get_preferences


def _event_datetime(value: dict, timezone_name: str) -> tuple[datetime, bool]:
    zone = ZoneInfo(value.get("timeZone") or timezone_name)
    if value.get("dateTime"):
        result = datetime.fromisoformat(str(value["dateTime"]).replace("Z", "+00:00"))
        if result.tzinfo is None:
            result = result.replace(tzinfo=zone)
        return result, False
    if value.get("date"):
        day = date.fromisoformat(str(value["date"]))
        return datetime.combine(day, time.min, tzinfo=zone), True
    raise ValueError("Calendar event has no valid start or end time")


def get_calendar_busy_blocks(db: Session, user_id: int, start_at: datetime, end_at: datetime) -> CalendarBusyResponse:
    integration = get_google_integration(db, user_id)
    if integration is None:
        return CalendarBusyResponse(
            calendar_synced=False,
            busy_blocks=[],
            message="Google Calendar is not connected. Showing your saved task schedule only.",
        )

    preferences = get_preferences(db, user_id)
    try:
        service = build_calendar_service(db, user_id)
        payload = service.events().list(
            calendarId="primary",
            timeMin=start_at.astimezone(timezone.utc).isoformat(),
            timeMax=end_at.astimezone(timezone.utc).isoformat(),
            singleEvents=True,
            orderBy="startTime",
            maxResults=250,
        ).execute()
        integration.last_synced_at = datetime.now(timezone.utc)
        db.commit()
    except Exception:
        return CalendarBusyResponse(
            calendar_synced=False,
            busy_blocks=[],
            message="Google Calendar could not be loaded. Reconnect Google or retry later; saved schedules remain available.",
        )

    raw_items = payload.get("items", []) if isinstance(payload, dict) else []
    if not isinstance(raw_items, list):
        raw_items = []
    blocks: list[CalendarBusyBlock] = []
    for index, item in enumerate(raw_items):
        if not isinstance(item, dict) or item.get("status") == "cancelled" or item.get("transparency") == "transparent":
            continue
        try:
            start, all_day = _event_datetime(item.get("start") or {}, preferences.timezone_name)
            end, end_all_day = _event_datetime(item.get("end") or {}, preferences.timezone_name)
            if end <= start or end <= start_at or start >= end_at:
                continue
            title = item.get("summary")
            title = title.strip()[:255] if isinstance(title, str) and title.strip() else "Busy"
            block = CalendarBusyBlock.model_validate({
                "id": str(item.get("id") or f"calendar-event-{index}")[:255],
                "title": title,
                "start_at": start,
                "end_at": end,
                "all_day": all_day or end_all_day,
            })
            blocks.append(block)
        except (TypeError, ValueError):
            continue

    blocks.sort(key=lambda block: block.start_at)
    return CalendarBusyResponse(calendar_synced=True, busy_blocks=blocks)
