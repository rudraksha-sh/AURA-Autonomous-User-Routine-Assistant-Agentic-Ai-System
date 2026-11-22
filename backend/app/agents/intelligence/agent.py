from app.agents.intelligence.schemas import CapacityFinding
from app.schemas.daily_planner import SchedulePreviewResponse


def evaluate_capacity(schedule: SchedulePreviewResponse) -> CapacityFinding:
    remaining = sum(item.remaining_minutes or 0 for item in schedule.unscheduled)
    return CapacityFinding(remaining_minutes=remaining, fits_proposed_day=not schedule.unscheduled)
