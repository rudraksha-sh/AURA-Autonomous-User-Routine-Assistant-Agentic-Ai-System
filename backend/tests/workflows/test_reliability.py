import json
import sqlite3
import subprocess
import sys
from contextlib import closing
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import OperationalError

from app.db.session import SessionLocal
from app.models.task import Task
from app.models.workflow import WorkflowRun
from app.workflows import nodes, registry
from tests.workflows.test_autonomy_recovery import grant_for
from tests.workflows.test_goal_workflow import headers, start_plan


def transition(client, auth, run, operation):
    return client.post(f"/api/v1/workflows/{run['id']}/transition", headers=auth,
                       json={"operation": operation, "revision": run["revision"]})


def assert_pending(run, checkpoint):
    with SessionLocal() as db:
        row = db.get(WorkflowRun, run["id"])
        assert (row.status, row.revision, row.checkpoint) == ("awaiting_approval", 0, checkpoint)
        assert db.scalar(select(func.count(Task.id))) == 0


def test_fresh_process_reloads_and_approves_checkpoint(client, tmp_path, test_engine, test_schema):
    auth = headers(client, "restart@example.com")
    _, run = start_plan(client, auth)
    url = test_engine.url.render_as_string(hide_password=False)
    options = {}
    if test_engine.dialect.name == "sqlite":
        filename = tmp_path / "restart.db"
        with test_engine.connect() as connection, closing(sqlite3.connect(filename)) as target:
            connection.connection.driver_connection.backup(target)
        url = f"sqlite:///{filename.as_posix()}"
    else:
        options = {"options": f"-csearch_path={test_schema},public -c timezone=UTC"}

    result = subprocess.run(
        [sys.executable, "-c", """
import json
import sys
from uuid import UUID
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from app.models.task import Task
from app.workflows.registry import owned_run, transition

url, options, run_id, user_id = json.load(sys.stdin)
engine = create_engine(url, connect_args=options)
try:
    with Session(engine) as db:
        row = owned_run(db, user_id, UUID(run_id))
        assert row.checkpoint
        transition(db, row, "approve", 0)
        assert (row.status, row.revision, row.checkpoint) == ("completed", 1, [])
        assert db.scalar(select(func.count(Task.id))) == 5
finally:
    engine.dispose()
"""],
        input=json.dumps([url, options, run["id"], owned_user_id(run)]),
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr


def owned_user_id(run):
    with SessionLocal() as db:
        return db.get(WorkflowRun, run["id"]).user_id


def test_manual_rejection_and_approval_expiry(client):
    auth = headers(client, "review-expiry@example.com")
    _, run = start_plan(client, auth)
    with SessionLocal() as db:
        row = db.get(WorkflowRun, run["id"])
        row.created_at = datetime.now(timezone.utc) - timedelta(hours=25)
        checkpoint = row.checkpoint
        db.commit()

    assert transition(client, auth, run, "approve").status_code == 409
    assert_pending(run, checkpoint)
    response = transition(client, auth, run, "reject")
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "rejected"
    with SessionLocal() as db:
        assert db.get(WorkflowRun, run["id"]).checkpoint == []
        assert db.scalar(select(func.count(Task.id))) == 0


def test_cross_user_mutations_and_grant_are_denied(client):
    owner = headers(client, "reliability-owner@example.com")
    other = headers(client, "reliability-other@example.com")
    payload, run = start_plan(client, owner)
    assert transition(client, other, run, "approve").status_code == 404
    paused = transition(client, owner, run, "pause").json()
    for operation in ("resume", "cancel"):
        assert transition(client, other, paused, operation).status_code == 404
    other_payload, _ = start_plan(client, other)
    grant = grant_for(client, owner, payload["goal_id"])
    response = client.post("/api/v1/workflows", headers=other, json={
        **other_payload, "run_id": str(uuid4()), "grant_id": grant["id"],
    })
    assert response.status_code == 403
    resumed = transition(client, owner, paused, "resume").json()
    assert transition(client, owner, resumed, "approve").status_code == 200
    assert transition(client, owner, resumed, "approve").status_code == 409
    assert client.post("/api/v1/workflows", headers=owner, json=payload).json()["status"] == "completed"
    with SessionLocal() as db:
        assert db.scalar(select(func.count(Task.id))) == 5


@pytest.mark.parametrize("checkpoint", [[], [["put", "invalid", "not-base64"]]])
def test_unusable_checkpoint_can_be_cancelled_without_writes(client, checkpoint):
    auth = headers(client, "checkpoint-recovery@example.com")
    _, run = start_plan(client, auth)
    with SessionLocal() as db:
        db.get(WorkflowRun, run["id"]).checkpoint = checkpoint
        db.commit()
    response = transition(client, auth, run, "approve")
    assert response.status_code == 409
    assert "Cancel it and preview a new plan" in response.json()["message"]
    assert_pending(run, checkpoint)
    response = transition(client, auth, run, "cancel")
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    with SessionLocal() as db:
        assert db.get(WorkflowRun, run["id"]).checkpoint == []
        assert db.scalar(select(func.count(Task.id))) == 0


def test_database_failure_after_task_flush_rolls_back_and_is_retryable(client, monkeypatch):
    auth = headers(client, "database-rollback@example.com")
    _, run = start_plan(client, auth)
    with SessionLocal() as db:
        checkpoint = db.get(WorkflowRun, run["id"]).checkpoint

    def fail_verification(db, *args):
        assert db.scalar(select(func.count(Task.id))) == 5
        db.execute(text("SELECT * FROM task03_missing_test_table"))

    with monkeypatch.context() as patch:
        patch.setattr(nodes, "verify_tasks", fail_verification)
        response = transition(client, auth, run, "approve")
        assert response.status_code == 500
        assert "task03_missing_test_table" not in response.text
    assert_pending(run, checkpoint)
    assert transition(client, auth, run, "approve").status_code == 200


def test_database_timeout_allows_same_revision_retry(client, monkeypatch, test_engine):
    auth = headers(client, "database-timeout@example.com")
    _, run = start_plan(client, auth)
    with SessionLocal() as db:
        checkpoint = db.get(WorkflowRun, run["id"]).checkpoint

    def short_lock_timeout(db):
        db.execute(text("SET LOCAL lock_timeout = '100ms'"))

    def mock_timeout(db, *args):
        class LockTimeout(Exception):
            sqlstate = "55P03"

        raise OperationalError(None, None, LockTimeout())

    with monkeypatch.context() as patch:
        if test_engine.dialect.name == "postgresql":
            patch.setattr(registry, "_set_transaction_limits", short_lock_timeout)
            with SessionLocal() as lock_db:
                lock_db.scalar(select(WorkflowRun).where(WorkflowRun.id == run["id"]).with_for_update())
                response = transition(client, auth, run, "approve")
        else:
            patch.setattr(registry, "lock_revision", mock_timeout)
            response = transition(client, auth, run, "approve")
        assert response.status_code == 503, response.text
        assert response.headers["Retry-After"] == "1"
    assert_pending(run, checkpoint)
    assert transition(client, auth, run, "approve").status_code == 200
