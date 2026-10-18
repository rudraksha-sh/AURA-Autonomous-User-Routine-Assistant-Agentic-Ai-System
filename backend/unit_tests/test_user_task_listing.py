from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.session import Base
from app.models import Goal, Task, User
from app.services.task_service import get_user_tasks
from app.schemas.task import TaskCreate, TaskUpdate
from pydantic import ValidationError


def test_user_task_listing_only_returns_tasks_from_owned_goals(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'tasks.db'}")
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as session:
            owner = User(email="owner@example.com", password_hash="x", name="Owner")
            other = User(email="other@example.com", password_hash="x", name="Other")
            session.add_all([owner, other])
            session.flush()
            owner_goal = Goal(user_id=owner.id, title="Owner goal")
            other_goal = Goal(user_id=other.id, title="Other goal")
            session.add_all([owner_goal, other_goal])
            session.flush()
            owner_task = Task(goal_id=owner_goal.id, title="Owner task")
            other_task = Task(goal_id=other_goal.id, title="Other task")
            session.add_all([owner_task, other_task])
            session.commit()

            tasks = get_user_tasks(session, owner.id)

            assert [task.id for task in tasks] == [owner_task.id]
    finally:
        engine.dispose()


def test_task_payloads_validate_priority_and_status():
    assert TaskCreate(title="Write", priority="high").priority == "high"
    assert TaskUpdate(status="completed").status == "completed"

    try:
        TaskCreate(title="Write", priority="urgent")
    except ValidationError:
        pass
    else:
        raise AssertionError("Unsupported task priority should be rejected")

    try:
        TaskUpdate(status="done")
    except ValidationError:
        pass
    else:
        raise AssertionError("Unsupported task status should be rejected")
