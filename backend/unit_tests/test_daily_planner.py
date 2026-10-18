from datetime import date, datetime, time, timedelta, timezone

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.session import Base
from app.models.goal import Goal
from app.models.task import Task
from app.models.user import User
from app.schemas.daily_planner import PlanningPreferencesInput, ScheduleSaveRequest
from app.services.daily_planner_service import preview_daily_schedule, read_daily_schedule, save_daily_schedule, update_preferences


def test_daily_schedule_splits_sessions_and_explains_priority(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'daily-planner.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = User(email="schedule@example.com", password_hash="unused", name="Schedule")
        db.add(user)
        db.flush()
        goal = Goal(user_id=user.id, title="Prepare report", status="active")
        db.add(goal)
        db.flush()
        due_soon = Task(goal_id=goal.id, title="Urgent research", priority="high", estimated_minutes=100,
                        deadline=datetime(2026, 10, 19, 12, tzinfo=timezone.utc), position=1)
        later = Task(goal_id=goal.id, title="Format report", priority="low", estimated_minutes=40,
                     deadline=datetime(2026, 11, 1, 12, tzinfo=timezone.utc), position=2)
        db.add_all([due_soon, later])
        db.commit()

        update_preferences(db, user.id, PlanningPreferencesInput(
            timezone_name="America/New_York", workday_start=time(9), workday_end=time(17),
            preferred_session_minutes=50, break_minutes=10, daily_capacity_minutes=120,
        ))
        preview = preview_daily_schedule(db, user.id, date(2026, 10, 18))
        assert preview.scheduled_minutes == 120
        assert [entry.task_id for entry in preview.entries[:2]] == [due_soon.id, due_soon.id]
        assert preview.entries[0].start_at.hour == 9
        assert preview.entries[1].start_at - preview.entries[0].end_at == timedelta(minutes=10)
        assert preview.unscheduled
        assert "deadline" in preview.entries[0].explanation


def test_schedule_save_checks_overlaps_capacity_and_ownership(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'schedule-save.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = User(email="schedule-owner@example.com", password_hash="unused", name="Owner")
        other = User(email="schedule-other@example.com", password_hash="unused", name="Other")
        db.add_all([user, other])
        db.flush()
        goal = Goal(user_id=user.id, title="Owned goal", status="active")
        other_goal = Goal(user_id=other.id, title="Other goal", status="active")
        db.add_all([goal, other_goal])
        db.flush()
        task = Task(goal_id=goal.id, title="Owned task", priority="medium", estimated_minutes=45, position=1)
        foreign_task = Task(goal_id=other_goal.id, title="Private task", priority="medium", estimated_minutes=45, position=1)
        db.add_all([task, foreign_task])
        db.commit()
        update_preferences(db, user.id, PlanningPreferencesInput(
            timezone_name="UTC", workday_start=time(9), workday_end=time(17),
            preferred_session_minutes=45, break_minutes=10, daily_capacity_minutes=360,
        ))

        bad_overlap = ScheduleSaveRequest.model_validate({
            "idempotency_key": "551a3691-1469-4b64-9c8d-10ff1eb77f71",
            "target_date": "2026-10-19",
            "entries": [
                {"task_id": task.id, "start_at": "2026-10-19T09:00:00Z", "duration_minutes": 30},
                {"task_id": task.id, "start_at": "2026-10-19T09:20:00Z", "duration_minutes": 15},
            ],
        })
        with pytest.raises(ValueError, match="overlap"):
            save_daily_schedule(db, user.id, bad_overlap)

        foreign_request = ScheduleSaveRequest.model_validate({
            "idempotency_key": "551a3691-1469-4b64-9c8d-10ff1eb77f72",
            "target_date": "2026-10-19",
            "entries": [{"task_id": foreign_task.id, "start_at": "2026-10-19T09:00:00Z", "duration_minutes": 30}],
        })
        with pytest.raises(LookupError):
            save_daily_schedule(db, user.id, foreign_request)

        good_request = ScheduleSaveRequest.model_validate({
            "idempotency_key": "551a3691-1469-4b64-9c8d-10ff1eb77f73",
            "target_date": "2026-10-19",
            "entries": [{"task_id": task.id, "start_at": "2026-10-19T09:00:00Z", "duration_minutes": 45}],
        })
        first = save_daily_schedule(db, user.id, good_request)
        repeated = save_daily_schedule(db, user.id, good_request)
        assert first.id == repeated.id
        assert len(read_daily_schedule(db, user.id, date(2026, 10, 19)).entries) == 1


def test_planning_preferences_reject_invalid_timezone_or_workday():
    with pytest.raises(ValidationError):
        PlanningPreferencesInput(timezone_name="Mars/Olympus")
    with pytest.raises(ValidationError):
        PlanningPreferencesInput(workday_start=time(17), workday_end=time(9))
    with pytest.raises(ValidationError):
        PlanningPreferencesInput(workday_start=time(9), workday_end=time(10), daily_capacity_minutes=90)
