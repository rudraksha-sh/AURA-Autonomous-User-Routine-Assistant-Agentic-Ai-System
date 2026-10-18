from datetime import date, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.models.goal import Goal
from app.schemas.planner import PlanRequest, PlanSaveRequest
from app.services.planner_service import generate_goal_plan


def test_rule_plan_is_deterministic_and_uses_goal_deadline():
    goal = Goal(id=11, title="Learn watercolor", description="Practice landscapes", deadline=datetime(2026, 11, 1, tzinfo=timezone.utc))
    first = generate_goal_plan(goal, 5, today=date(2026, 10, 18))
    second = generate_goal_plan(goal, 5, today=date(2026, 10, 18))
    assert first.model_dump() == second.model_dump()
    assert len(first.tasks) == 5
    assert all(task.deadline and task.deadline.date() <= date(2026, 11, 1) for task in first.tasks)
    assert all("Learn watercolor" in task.title for task in first.tasks)
    assert [task.position for task in first.tasks] == [1, 2, 3, 4, 5]


def test_rule_plan_without_valid_deadline_does_not_invent_dates():
    goal = Goal(id=12, title="Organize notes", description=None, deadline=None)
    no_deadline = generate_goal_plan(goal, 3, today=date(2026, 10, 18))
    past_deadline = generate_goal_plan(Goal(id=13, title="Past due", deadline=datetime(2026, 10, 17, tzinfo=timezone.utc)), 3, today=date(2026, 10, 18))
    assert all(task.deadline is None for task in no_deadline.tasks)
    assert all(task.deadline is None for task in past_deadline.tasks)
    assert all(task.description and "Goal: Organize notes" in task.description for task in no_deadline.tasks)


def test_planning_input_validation():
    with pytest.raises(ValidationError):
        PlanRequest(task_count=2)
    with pytest.raises(ValidationError):
        PlanSaveRequest(idempotency_key="3a843265-c481-461f-ae0c-4c158b4ed116", tasks=[
            {"title": "   ", "estimated_minutes": 30, "position": 1},
        ])
    with pytest.raises(ValidationError):
        PlanSaveRequest(idempotency_key="3a843265-c481-461f-ae0c-4c158b4ed116", tasks=[
            {"title": "One", "estimated_minutes": 30, "position": 1},
            {"title": "Two", "estimated_minutes": 30, "position": 1},
        ])
    with pytest.raises(ValidationError):
        PlanSaveRequest(idempotency_key="3a843265-c481-461f-ae0c-4c158b4ed116", tasks=[
            {"title": "Past date", "estimated_minutes": 30, "position": 1, "deadline": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()},
        ])
