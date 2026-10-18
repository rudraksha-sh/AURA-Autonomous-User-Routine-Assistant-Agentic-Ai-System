"""Create fictional AURA sample data in an explicitly selected SQLite database.

Run from ``backend`` with AURA_SEED_DATABASE_URL set to a SQLite file under
``backend/sample_data`` and AURA_SEED_USER_PASSWORD set to a local-only password.
The script only adds missing sample records; it never deletes or overwrites data.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
SAMPLE_DIR = (BACKEND_DIR / "sample_data").resolve()
SAMPLE_EMAIL = "aura.sample@example.com"
SAMPLE_NAME = "Alex Morgan (Sample)"


def _safe_database_url() -> str:
    url = os.environ.get("AURA_SEED_DATABASE_URL", "").strip()
    if not url.startswith("sqlite:///"):
        raise SystemExit("Set AURA_SEED_DATABASE_URL to a dedicated SQLite file under backend/sample_data.")
    raw_path = url.removeprefix("sqlite:///")
    if raw_path == ":memory:":
        raise SystemExit("Use a persistent, dedicated SQLite file so sample data survives process exit.")
    path = Path(raw_path)
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    else:
        path = path.resolve()
    if SAMPLE_DIR not in path.parents or "test" not in path.name.lower():
        raise SystemExit(f"Refusing database path outside the dedicated sample test directory: {path}")
    return f"sqlite:///{path.as_posix()}"


def main() -> None:
    database_url = _safe_database_url()
    password = os.environ.get("AURA_SEED_USER_PASSWORD", "")
    if len(password) < 8:
        raise SystemExit("Set AURA_SEED_USER_PASSWORD to a local-only password of at least 8 characters.")
    if Path.cwd().resolve() != BACKEND_DIR:
        raise SystemExit("Run this script from the backend directory so the existing backend .env is loaded correctly.")

    # Override the normal configured database before importing application modules.
    os.environ["DATABASE_URL"] = database_url
    sys.path.insert(0, str(BACKEND_DIR))

    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session

    from app.core.security import hash_password
    from app.db.session import Base
    from app.main import app
    from app.models.goal import Goal
    from app.models.task import Task
    from app.models.user import User

    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    path = Path(database_url.removeprefix("sqlite:///"))
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)

    now = datetime.now(timezone.utc).replace(microsecond=0)
    goals = [
        {"title": "Prepare for Machine Learning exams within 14 days", "description": "Prepare core theory, practice implementations, and complete a timed revision test.", "priority": "high", "days": 14},
        {"title": "Build an AI-powered productivity application within 30 days", "description": "Deliver reliable orchestration, API behavior, and automated backend coverage for AURA.", "priority": "high", "days": 30},
        {"title": "Establish a consistent daily study routine within 21 days", "description": "Build a sustainable daily review habit and track progress consistently.", "priority": "medium", "days": 21},
    ]
    task_specs = {
        goals[0]["title"]: [
            ("Study Python and NumPy", "Review array operations, broadcasting, and short numerical exercises.", 60, "high", "completed", -2),
            ("Learn linear and logistic regression", "Compare the models, assumptions, loss functions, and evaluation methods.", 90, "high", "in_progress", 1),
            ("Complete ML coding exercises", "Implement selected model and preprocessing exercises, then record mistakes.", 45, "medium", "pending", -1),
            ("Revise ML notes", "Review lecture notes and make a concise list of concepts that need another pass.", 30, "medium", "pending", 5),
            ("Complete a practice test", "Take a timed practice test and review each incorrect answer.", 60, "high", "pending", 10),
        ],
        goals[1]["title"]: [
            ("Implement AURA agent orchestration", "Connect the approved deterministic tools and validate ownership and outcomes.", 120, "high", "in_progress", 4),
            ("Write backend tests", "Cover authenticated API behavior, validation, persistence, and user isolation.", 60, "medium", "pending", 12),
        ],
        goals[2]["title"]: [
            ("Review weekly progress", "Summarize study sessions, note blockers, and choose one adjustment for next week.", 30, "low", "pending", 3),
        ],
    }

    created_goals = created_tasks = 0
    try:
        with Session(engine) as db:
            user = db.scalar(select(User).where(User.email == SAMPLE_EMAIL))
            if user is None:
                user = User(email=SAMPLE_EMAIL, name=SAMPLE_NAME, password_hash=hash_password(password))
                db.add(user)
                db.commit()
                db.refresh(user)
            elif user.name != SAMPLE_NAME:
                raise SystemExit("The sample email already belongs to a different profile; no data was changed.")
            user_id = user.id

        with TestClient(app) as client:
            login = client.post("/api/auth/login", json={"email": SAMPLE_EMAIL, "password": password})
            if login.status_code != 200:
                raise SystemExit(f"Sample user login failed ({login.status_code}); existing account was not modified.")
            headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

            response = client.get("/api/goals", headers=headers)
            response.raise_for_status()
            existing_goals = {item["title"]: item for item in response.json()}
            goal_ids: dict[str, int] = {}
            for spec in goals:
                goal = existing_goals.get(spec["title"])
                if goal is None:
                    created = client.post("/api/goals", headers=headers, json={
                        "title": spec["title"], "description": spec["description"], "priority": spec["priority"],
                        "status": "active", "deadline": (now + timedelta(days=spec["days"])).isoformat(),
                    })
                    created.raise_for_status()
                    goal = created.json()
                    created_goals += 1
                goal_ids[spec["title"]] = goal["id"]

            all_existing = client.get("/api/tasks", headers=headers)
            all_existing.raise_for_status()
            seen = {(task["goal_id"], task["title"]) for task in all_existing.json()}
            for goal_title, specs in task_specs.items():
                goal_id = goal_ids[goal_title]
                for position, (title, description, estimate, priority, status, due_in) in enumerate(specs, start=1):
                    if (goal_id, title) in seen:
                        continue
                    created = client.post(f"/api/tasks/goals/{goal_id}/tasks", headers=headers, json={
                        "title": title, "description": description, "estimated_minutes": estimate,
                        "priority": priority, "status": status, "position": position,
                        "deadline": (now + timedelta(days=due_in)).isoformat(),
                    })
                    created.raise_for_status()
                    seen.add((goal_id, title))
                    created_tasks += 1

            final_goals = client.get("/api/goals", headers=headers)
            final_tasks = client.get("/api/tasks", headers=headers)
            final_goals.raise_for_status()
            final_tasks.raise_for_status()
            print(f"Database: {path}")
            print(f"Sample profile: {SAMPLE_EMAIL} (password not displayed)")
            print(f"Newly created: {created_goals} goals, {created_tasks} tasks")
            print(f"Total for sample profile: {len(final_goals.json())} goals, {len(final_tasks.json())} tasks")
            print("Authenticated API reads verified after seeding.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
