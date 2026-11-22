from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.autonomy import AutonomyGrant
from app.models.task import Task
from tests.conftest import test_engine
from tests.workflows.test_goal_workflow import headers, start_plan


def grant_for(client, auth, goal_id):
    response = client.post("/api/v1/autonomy/grants", headers=auth, json={
        "goal_id": goal_id, "operation": "goal.tasks.create", "duration_minutes": 10,
        "run_limit": 1, "task_limit": 5, "consent": True, "consent_version": "local-task-grant-v1",
    })
    assert response.status_code == 201, response.text
    return response.json()


def run_with_grant(client, auth, payload, grant):
    return client.post("/api/v1/workflows", headers=auth, json={
        **payload, "run_id": str(uuid4()), "grant_id": grant["id"],
    })


def test_scope_budget_and_explicit_undo(client):
    auth = headers(client, "grant-owner@example.com")
    other = headers(client, "grant-other@example.com")
    payload, _ = start_plan(client, auth)
    different_goal, _ = start_plan(client, auth)
    grant = grant_for(client, auth, payload["goal_id"])
    assert run_with_grant(client, auth, different_goal, grant).status_code == 403
    assert client.post(f"/api/v1/autonomy/grants/{grant['id']}/transition", headers=other,
                       json={"operation": "revoke"}).status_code == 404
    response = run_with_grant(client, auth, payload, grant)
    assert response.status_code == 201, response.text
    run = response.json()
    assert run["status"] == "completed"
    assert run["result"]["evidence"]["grant_id"] == grant["id"]
    assert client.get("/api/v1/autonomy/grants", headers=auth).json()[0]["status"] == "exhausted"
    assert run_with_grant(client, auth, payload, grant).status_code == 403
    undo_url = f"/api/v1/workflows/{run['id']}/undo"
    assert client.post(undo_url, headers=auth, json={"revision": 0, "confirm": False}).status_code == 422
    undone = client.post(undo_url, headers=auth, json={"revision": 0, "confirm": True})
    assert undone.status_code == 200, undone.text
    assert undone.json()["status"] == "undone"
    assert client.post(undo_url, headers=auth, json={"revision": 0, "confirm": True}).status_code == 409
    status = client.get(f"/api/v1/workflows/{run['id']}/verification", headers=auth)
    assert status.json()["status"] == "unverified"
    with SessionLocal() as db:
        assert list(db.scalars(select(Task))) == []


def test_expiry_pause_and_emergency_stop(client):
    auth = headers(client, "grant-stop@example.com")
    payload, _ = start_plan(client, auth)
    grant = grant_for(client, auth, payload["goal_id"])
    transition_url = f"/api/v1/autonomy/grants/{grant['id']}/transition"
    assert client.post(transition_url, headers=auth, json={"operation": "pause"}).json()["status"] == "paused"
    assert run_with_grant(client, auth, payload, grant).status_code == 403
    assert client.post(transition_url, headers=auth, json={"operation": "resume"}).json()["status"] == "active"
    with SessionLocal() as db:
        stored = db.get(AutonomyGrant, grant["id"])
        stored.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
    assert run_with_grant(client, auth, payload, grant).status_code == 403
    assert client.get("/api/v1/autonomy/grants", headers=auth).json()[0]["status"] == "expired"
    fresh = grant_for(client, auth, payload["goal_id"])
    assert client.post("/api/v1/autonomy/stop", headers=auth).status_code == 204
    assert run_with_grant(client, auth, payload, fresh).status_code == 403


def test_application_undo_refuses_edited_tasks(client):
    auth = headers(client, "undo-edited@example.com")
    _, run = start_plan(client, auth)
    path = f"/api/v1/workflows/{run['id']}"
    approved = client.post(path + "/transition", headers=auth, json={"operation": "approve", "revision": 0})
    assert approved.status_code == 200, approved.text
    task_id = approved.json()["result"]["evidence"]["task_ids"][0]
    with SessionLocal() as db:
        db.get(Task, task_id).title = "My revised task"
        db.commit()
    undo = client.post(path + "/undo", headers=auth, json={"confirm": True, "revision": 1})
    assert undo.status_code == 409
    assert client.get(path, headers=auth).json()["revision"] == 1


@pytest.mark.skipif(test_engine.dialect.name != "postgresql", reason="requires independent PostgreSQL connections")
def test_concurrent_approvals_commit_one_task_batch(client):
    auth = headers(client, "approval-race@example.com")
    _, run = start_plan(client, auth)
    url = f"/api/v1/workflows/{run['id']}/transition"

    def approve():
        return client.post(url, headers=auth, json={"operation": "approve", "revision": 0}).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: approve(), range(2)))
    assert sorted(outcomes) == [200, 409]
    with SessionLocal() as db:
        assert len(list(db.scalars(select(Task)))) == 5


@pytest.mark.skipif(test_engine.dialect.name != "postgresql", reason="requires independent PostgreSQL connections")
def test_concurrent_grant_use_respects_single_execution_limit(client):
    auth = headers(client, "grant-race@example.com")
    payload, _ = start_plan(client, auth)
    grant = grant_for(client, auth, payload["goal_id"])
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: run_with_grant(client, auth, payload, grant).status_code, range(2)))
    assert sorted(outcomes) == [201, 403]
    with SessionLocal() as db:
        assert len(list(db.scalars(select(Task)))) == 5
