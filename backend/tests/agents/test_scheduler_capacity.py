from datetime import date, datetime, timezone
from types import SimpleNamespace

from app.agents.intelligence.agent import evaluate_capacity
from app.schemas.daily_planner import PlanningPreferencesResponse, ScheduledTaskProposal
from app.services.daily_planner_service import schedule_tasks


def test_saved_slots_reserve_time_and_reduce_remaining_capacity():
    target = date(2030, 1, 2)
    reserved = ScheduledTaskProposal(
        task_id=11, title="Existing appointment", priority="high", segment_index=1,
        start_at=datetime(2030, 1, 2, 9, 0, tzinfo=timezone.utc),
        end_at=datetime(2030, 1, 2, 10, 0, tzinfo=timezone.utc),
        duration_minutes=60, explanation="Saved schedule",
    )
    slot = SimpleNamespace(id=-1, position=1, title="Practice", priority="high", deadline=None,
                           created_at=None, estimated_minutes=120)
    schedule = schedule_tasks(PlanningPreferencesResponse(daily_capacity_minutes=90), target,
                              [slot], reserved=(reserved,))
    assert schedule.entries[0].start_at == datetime(2030, 1, 2, 10, 10, tzinfo=timezone.utc)
    assert schedule.scheduled_minutes == schedule.capacity_minutes == 30
    capacity = evaluate_capacity(schedule)
    assert capacity.remaining_minutes == 90
    assert capacity.fits_proposed_day is False

    assert capacity.workload_minutes == 120
    assert capacity.workload_pressure_pct == 400
    assert capacity.schedule_feasibility_pct == 25
    assert capacity.reasons
