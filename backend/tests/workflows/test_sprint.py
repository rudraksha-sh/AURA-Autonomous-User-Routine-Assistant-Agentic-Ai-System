from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from cryptography.fernet import Fernet
from pydantic import SecretStr
from sqlalchemy import func, select

from app.core.config import settings
from app.db.session import SessionLocal
from app.integrations.google import reads
from app.models.planning import DailySchedule
from app.models.task import Task
from app.models.user import User
from app.services.integration_service import upsert_google_integration
from app.workflows import nodes
from tests.workflows.test_goal_workflow import headers, start_plan
from tests.workflows.test_reliability import transition

ROOT = "/api/v1/workflows"


def test_google_consent_scope_and_calendar_workflow(client, monkeypatch):
    owner_email = "sprint-google@example.com"
    auth = headers(client, owner_email)
    other = headers(client, "sprint-google-other@example.com")
    monkeypatch.setattr(settings, "integration_token_key", SecretStr(Fernet.generate_key().decode()))
    with SessionLocal() as db:
        owner = db.scalar(select(User.id).where(User.email == owner_email))
        integration = upsert_google_integration(
            db, user_id=owner, provider_account_id="fixture", access_token="fixture-token", refresh_token="fixture-refresh",
            token_expiry=datetime.now(timezone.utc) + timedelta(hours=1),
            scopes=" ".join(reads.SCOPE + scope for scope in ("gmail.readonly", "drive.readonly", "calendar.freebusy")),
        )
        assert integration.access_token.startswith("fernet:v1:")

    consent = client.get("/api/integrations/google/connect?service=calendar", headers=auth)
    requested = parse_qs(urlparse(consent.json()["authorization_url"]).query)["scope"][0].split()
    assert requested == ["openid", reads.SCOPE + "userinfo.email", reads.SCOPE + "calendar.freebusy"]

    calls = []

    def fake(method, url, token, **kwargs):
        assert token == "fixture-token"
        calls.append((method, url, kwargs))
        if url.endswith("/freeBusy"):
            return {"calendars": {"primary": {"busy": [
                {"start": "2030-01-02T09:00:00Z", "end": "2030-01-02T12:00:00Z"},
            ]}}}
        if kwargs.get("as_text"):
            return "Fixture Drive document"
        if kwargs["params"].get("fields") == "mimeType,trashed":
            return {"mimeType": "application/vnd.google-apps.document", "trashed": False}
        if url.endswith("/messages/m1"):
            return {"id": "m1", "payload": {}}
        return {"messages": [{"id": "m1"}]} if "gmail" in url else {"files": [{"id": "file1"}]}

    monkeypatch.setattr(reads, "_request", fake)
    path = "/api/integrations/google/read"
    assert client.post(path, headers=auth, json={"service": "gmail", "authorized": False}).status_code == 403
    assert client.post(path, headers=other, json={"service": "gmail", "authorized": True}).status_code == 403
    assert not calls
    assert client.post(path, headers=auth, json={"service": "gmail", "authorized": True, "query": "orbit"}).status_code == 200
    assert calls[-1][2]["params"] == {"q": "orbit", "maxResults": 20}
    assert client.post(path, headers=auth, json={"service": "gmail", "authorized": True, "item_id": "m1"}).status_code == 200
    assert calls[-1][2]["params"] == {"format": "full"}
    assert client.post(path, headers=auth, json={"service": "drive", "authorized": True, "item_id": "file1"}).json() == {
        "text": "Fixture Drive document",
    }
    payload, _ = start_plan(client, auth)
    preview = client.post(ROOT, headers=auth, json={**payload, "run_id": str(uuid4()), "include_calendar": True})
    assert preview.status_code == 201, preview.text
    schedule = preview.json()["result"]["schedule"]
    assert schedule["calendar_status"] == "included"
    assert schedule["entries"]
    assert all(datetime.fromisoformat(entry["start_at"]).hour >= 12 for entry in schedule["entries"])
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(DailySchedule)) == 0
    assert client.put("/api/planner/preferences", headers=auth, json={"timezone_name": "Europe/Berlin"}).status_code == 200
    task = client.post(f"/api/tasks/goals/{payload['goal_id']}/tasks", headers=auth,
                       json={"title": "Existing work", "estimated_minutes": 30}).json()
    booked = client.post("/api/planner/schedules", headers=auth, json={
        "target_date": payload["target_date"], "idempotency_key": str(uuid4()),
        "entries": [{"task_id": task["id"], "start_at": "2030-01-02T09:00:00Z", "duration_minutes": 30}],
    })
    assert booked.status_code == 201, booked.text
    conflict = client.post(ROOT, headers=auth, json={**payload, "run_id": str(uuid4()), "include_calendar": True})
    assert conflict.status_code == 201, conflict.text
    assert conflict.json()["result"]["schedule"]["calendar_conflict_task_ids"] == [task["id"]]

    revoked = []
    monkeypatch.setattr(reads, "revoke", lambda integration: revoked.append(integration.user_id))
    assert client.delete("/api/integrations/google?revoke_provider=true", headers=auth).status_code == 204
    assert revoked == [owner]
    fallback = client.post(ROOT, headers=auth, json={**payload, "run_id": str(uuid4()), "include_calendar": True})
    assert fallback.json()["result"]["schedule"]["calendar_status"] == "unavailable"


def test_memory_opt_in_and_revocation_stale_preview(client):
    auth = headers(client, "sprint-memory@example.com")
    other = headers(client, "sprint-memory-other@example.com")
    root = "/api/v1/memory"
    assert client.post(root, headers=auth, json={"text": "api_key=private"}).status_code == 422
    body = {"text": "Prefer a quiet workspace", "use_for_planning": True}
    response = client.post(root, headers=auth, json=body)
    assert response.status_code == 201, response.text
    path = f"{root}/{response.json()['id']}"
    assert client.get(root, headers=other).json() == []
    assert client.put(path, headers=other, json=body).status_code == 404
    assert client.delete(path, headers=other).status_code == 404
    _, run = start_plan(client, auth)
    assert "Review your saved planning memories" in run["result"]["plan"]["tasks"][1]["description"]
    assert body["text"] not in str(run)
    assert client.put(path, headers=auth, json={**body, "use_for_planning": False}).status_code == 200
    assert transition(client, auth, run, "approve").status_code == 409
    assert client.delete(root, headers=auth).status_code == 204
    assert client.get(root, headers=auth).json() == []


def test_simulation_deadline_and_unavailable_time_are_deterministic(client):
    auth = headers(client, "sprint-sim@example.com")
    other = headers(client, "sprint-sim-other@example.com")
    payload, _ = start_plan(client, auth)
    response = client.post(f"/api/tasks/goals/{payload['goal_id']}/tasks", headers=auth,
                           json={"title": "Prepare", "estimated_minutes": 60})
    assert response.status_code == 201, response.text
    task_id = response.json()["id"]
    scenario = {
        "target_date": "2030-01-02", "capacity_minutes": 120,
        "deadline_change": {"task_id": task_id, "deadline": "2030-01-02T09:30:00Z"},
        "unavailable_start_at": "2030-01-02T09:00:00Z", "unavailable_minutes": 30,
    }
    path = "/api/planner/schedules/what-if"
    first = client.post(path, headers=auth, json=scenario)
    assert first.status_code == 200, first.text
    assert first.json() == client.post(path, headers=auth, json=scenario).json()
    assert first.json()["baseline"]["fits"] is True
    assert first.json()["simulated"]["remaining_minutes"] == 60
    assert first.json()["potential_deadline_conflicts"]
    assert client.post(path, headers=other, json=scenario).status_code == 422
    with SessionLocal() as db:
        assert db.get(Task, task_id).deadline is None
        assert db.scalar(select(func.count()).select_from(DailySchedule)) == 0


def test_replan_preserves_and_reconciles_with_stale_and_atomic_guards(client, monkeypatch):
    auth = headers(client, "sprint-replan@example.com")
    payload, original = start_plan(client, auth)
    finished = transition(client, auth, original, "approve")
    assert finished.status_code == 200, finished.text
    ids = finished.json()["result"]["evidence"]["task_ids"]
    with SessionLocal() as db:
        db.get(Task, ids[0]).status = "completed"
        db.get(Task, ids[1]).title = "Manual task title"
        db.commit()
    assert client.patch(f"/api/goals/{payload['goal_id']}", headers=auth, json={"title": "Updated goal"}).status_code == 200

    def preview():
        result = client.post(ROOT, headers=auth, json={**payload, "run_id": str(uuid4()), "previous_run_id": original["id"]})
        assert result.status_code == 201, result.text
        return result.json()

    stale = preview()
    with SessionLocal() as db:
        db.get(Task, ids[3]).notes = "Edited after preview"
        db.commit()
    assert transition(client, auth, stale, "approve").status_code == 409
    revised = preview()
    assert revised["result"]["comparison"]["preserved_task_ids"] == [ids[0], ids[1], ids[3]]
    assert revised["result"]["comparison"]["updated_task_ids"] == [ids[2], ids[4]]
    sibling = preview()

    def fail(*args):
        raise RuntimeError("Injected verification failure")

    with monkeypatch.context() as patch:
        patch.setattr(nodes, "verify_tasks", fail)
        assert transition(client, auth, revised, "approve").status_code == 500
    with SessionLocal() as db:
        assert "Updated goal" not in db.get(Task, ids[2]).title
        assert db.scalar(select(func.count()).select_from(Task)) == 5

    result = transition(client, auth, revised, "approve")
    assert result.status_code == 200, result.text
    assert result.json()["result"]["evidence"]["task_ids"] == ids
    assert transition(client, auth, sibling, "approve").status_code == 409
    with SessionLocal() as db:
        assert db.get(Task, ids[0]).status == "completed"
        assert db.get(Task, ids[1]).title == "Manual task title"
        assert "Updated goal" in db.get(Task, ids[2]).title
        assert db.scalar(select(func.count()).select_from(Task)) == 5
