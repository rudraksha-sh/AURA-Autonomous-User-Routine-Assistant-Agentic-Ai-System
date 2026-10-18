from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.session import Base
from app.models import Goal, Task, User


def test_goal_and_task_created_at_defaults_are_datetimes(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'models.db'}")

    try:
        Base.metadata.create_all(engine)

        with Session(engine) as session:
            user = User(
                email="sqlite-defaults@example.com",
                password_hash="not-a-real-password-hash",
                name="SQLite Defaults",
            )
            session.add(user)
            session.flush()

            goal = Goal(user_id=user.id, title="Test goal")
            session.add(goal)
            session.flush()

            task = Task(goal_id=goal.id, title="Test task")
            session.add(task)
            session.commit()
            session.refresh(goal)
            session.refresh(task)

            assert isinstance(goal.created_at, datetime)
            assert isinstance(task.created_at, datetime)
    finally:
        engine.dispose()


def test_created_at_defaults_work_with_existing_sqlite_schema(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")

    try:
        Base.metadata.create_all(engine)

        with engine.begin() as connection:
            connection.exec_driver_sql("DROP TABLE tasks")
            connection.exec_driver_sql("DROP TABLE goals")
            connection.exec_driver_sql(
                """
                CREATE TABLE goals (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    description TEXT,
                    status VARCHAR(50) NOT NULL,
                    priority VARCHAR(20) NOT NULL,
                    deadline DATETIME,
                    created_at DATETIME NOT NULL DEFAULT 'now()',
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.exec_driver_sql(
                """
                CREATE TABLE tasks (
                    id INTEGER PRIMARY KEY,
                    goal_id INTEGER NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    description TEXT,
                    status VARCHAR(50) NOT NULL,
                    priority VARCHAR(20) NOT NULL,
                    estimated_minutes INTEGER,
                    deadline DATETIME,
                    position INTEGER NOT NULL,
                    created_at DATETIME NOT NULL DEFAULT 'now()',
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

        with Session(engine) as session:
            user = User(
                email="legacy-defaults@example.com",
                password_hash="not-a-real-password-hash",
                name="Legacy Defaults",
            )
            session.add(user)
            session.flush()

            goal = Goal(user_id=user.id, title="Legacy goal")
            session.add(goal)
            session.flush()

            task = Task(goal_id=goal.id, title="Legacy task")
            session.add(task)
            session.commit()
            session.refresh(goal)
            session.refresh(task)

            assert isinstance(goal.created_at, datetime)
            assert isinstance(task.created_at, datetime)
    finally:
        engine.dispose()
