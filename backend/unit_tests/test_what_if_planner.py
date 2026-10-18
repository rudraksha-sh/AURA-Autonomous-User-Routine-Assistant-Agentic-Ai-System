from datetime import date, datetime, time, timezone

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.session import Base
from app.models.goal import Goal
from app.models.planning import DailySchedule
from app.models.task import Task
from app.models.user import User
from app.schemas.daily_planner import PlanningPreferencesInput, WhatIfRequest
from app.services.daily_planner_service import update_preferences
from app.services.what_if_service import simulate_daily_schedule


def test_what_if_simulation_adds_proposed_task_and_never_persists_changes(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'what-if.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = User(email="what-if@example.com", password_hash="unused", name="What If")
        db.add(user)
        db.flush()
        goal = Goal(user_id=user.id, title="Prepare presentation", status="active")
        db.add(goal)
        db.flush()
        db.add(Task(goal_id=goal.id, title="Build slides", priority="medium", estimated_minutes=60, position=1))
        db.commit()
        update_preferences(db, user.id, PlanningPreferencesInput(
            timezone_name="UTC", workday_start=time(9), workday_end=time(17),
            preferred_session_minutes=45, break_minutes=10, daily_capacity_minutes=180,
        ))

        result = simulate_daily_schedule(db, user.id, WhatIfRequest.model_validate({
            "target_date": "2026-10-19",
            "capacity_minutes": 90,
            "proposed_task": {"title": "Urgent review", "estimated_minutes": 60, "priority": "high"},
            "unavailable_start_at": "2026-10-19T10:00:00Z",
            "unavailable_minutes": 30,
        }))

        assert result.baseline.capacity_minutes == 180
        assert result.simulated.capacity_minutes == 60
        assert any(entry.is_proposed_task for entry in result.simulated.entries + result.simulated.unscheduled)
        assert db.scalar(select(DailySchedule).where(DailySchedule.user_id == user.id)) is None
        assert db.scalar(select(Task).where(Task.title == "Urgent review")) is None
    engine.dispose()


def test_what_if_rejects_invalid_or_increasing_capacity():
    with pytest.raises(ValidationError):
        WhatIfRequest(target_date=date(2026, 10, 19))
    with pytest.raises(ValidationError):
        WhatIfRequest.model_validate({
            "target_date": "2026-10-19", "capacity_minutes": 30,
            "unavailable_start_at": "2026-10-19T09:00:00", "unavailable_minutes": 30,
        })

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = User(email="capacity@example.com", password_hash="unused", name="Capacity")
        db.add(user)
        db.commit()
        with pytest.raises(ValueError, match="cannot exceed"):
            simulate_daily_schedule(db, user.id, WhatIfRequest.model_validate({
                "target_date": "2026-10-19", "capacity_minutes": 361,
            }))
    engine.dispose()
