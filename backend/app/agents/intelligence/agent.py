from app.agents.intelligence.schemas import CapacityFinding
from app.schemas.daily_planner import SchedulePreviewResponse


def evaluate_capacity(schedule: SchedulePreviewResponse) -> CapacityFinding:
    remaining = sum(item.remaining_minutes or 0 for item in schedule.unscheduled)
    workload = schedule.scheduled_minutes + remaining
    deadline_risk = sum(item.deadline_conflict for item in schedule.unscheduled)
    conflicts = len(schedule.calendar_conflict_task_ids)
    reasons = []
    if remaining:
        reasons.append(f"{remaining} estimated minutes remain outside the proposed schedule.")
    if deadline_risk:
        reasons.append(f"{deadline_risk} tasks have remaining work that does not fit before their deadlines.")
    if conflicts:
        reasons.append(f"{conflicts} saved tasks overlap Google Calendar busy time.")
    if schedule.calendar_status == "unavailable":
        reasons.append("Google Calendar availability was unavailable.")
    if not reasons:
        reasons.append("All estimated work fits in the evaluated schedule.")
    return CapacityFinding(
        remaining_minutes=remaining, fits_proposed_day=not schedule.unscheduled and not conflicts,
        workload_minutes=workload,
        workload_pressure_pct=round(100 * workload / schedule.capacity_minutes) if schedule.capacity_minutes else None,
        schedule_feasibility_pct=round(100 * schedule.scheduled_minutes / workload) if workload else 100,
        deadline_risk_tasks=deadline_risk, calendar_conflicts=conflicts, reasons=reasons,
    )
