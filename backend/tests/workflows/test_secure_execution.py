from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event
from uuid import uuid4

import pytest

from app.agents.execution import adapters, outbox
from app.agents.execution.worker import dispatch_ready, metrics
from app.db.session import SessionLocal
from app.models.external_action import ExternalAction
from tests.workflows.test_goal_workflow import headers, start_plan
from tests.workflows.test_reliability import transition as workflow_transition

ROOT = "/api/v1/external-actions"


class FakeProvider:
    def __init__(self):
        self.calls = 0
        self.result = None
        self.fail = None
        self.during_apply = None

    def apply(self, *, key, resource, payload, fingerprint, timeout_seconds):
        assert resource.startswith("owner:") and timeout_seconds == 5
        self.calls += 1
        if self.during_apply:
            self.during_apply()
        if self.fail is adapters.NoEffectRetryable:
            raise self.fail()
        self.result = adapters.ProviderReceipt("fake-" + key, fingerprint)
        if self.fail:
            raise self.fail()
        return self.result

    def lookup(self, **kwargs):
        return self.result


@pytest.fixture
def provider(monkeypatch):
    fake = FakeProvider()
    monkeypatch.setattr(adapters, "get_adapter", lambda *scope: fake)
    return fake


def preview(client, auth, goal_id, **changes):
    body = {
        "goal_id": goal_id, "request_id": str(uuid4()), "provider": adapters.PROVIDER,
        "operation": adapters.OPERATION, "start_at": (outbox.now() + timedelta(hours=2)).isoformat(),
        "duration_minutes": 30, **changes,
    }
    response = client.post(ROOT, headers=auth, json=body)
    assert response.status_code == 201, response.text
    return body, response.json()


def move(client, auth, action, operation, **extra):
    return client.post(f"{ROOT}/{action['id']}/transition", headers=auth, json={
        "operation": operation, "revision": action["revision"], **extra,
    })


def confirm(client, auth, action):
    response = move(client, auth, action, "confirm", consent_version=action["consent_version"],
                    fingerprint=action["fingerprint"])
    assert response.status_code == 200, response.text
    return response.json()


def set_due(action):
    with SessionLocal() as db:
        db.get(ExternalAction, action["id"]).due_at = outbox.now() - timedelta(seconds=1)
        db.commit()


def test_consent_idempotency_pause_stop_and_tenant_scope(client, provider):
    auth = headers(client, "outbox-owner@example.com")
    other = headers(client, "outbox-other@example.com")
    payload, _ = start_plan(client, auth)
    body, action = preview(client, auth, payload["goal_id"])
    assert action["consent"] == "off" and provider.calls == 0
    assert client.post(ROOT, headers=auth, json=body).json()["id"] == action["id"]
    assert client.post(ROOT, headers=auth, json={**body, "duration_minutes": 45}).status_code == 409
    assert client.post(ROOT, headers=other, json=body).status_code == 404
    assert move(client, other, action, "confirm").status_code == 404
    assert move(client, auth, action, "dispatch").status_code == 409
    assert move(client, auth, action, "confirm").status_code == 403
    queued = confirm(client, auth, action)
    paused = move(client, auth, queued, "pause").json()
    assert move(client, auth, paused, "dispatch").status_code == 409
    resumed = move(client, auth, paused, "resume").json()
    assert resumed["consent"] == "active"
    assert client.post("/api/v1/autonomy/stop", headers=auth).status_code == 204
    latest = client.get(f"{ROOT}/{action['id']}", headers=auth).json()
    assert latest["consent"] == "revoked"
    assert move(client, auth, latest, "dispatch").status_code == 409
    assert provider.calls == 0


def test_goal_drift_and_expiry_block_dispatch(client, provider):
    auth = headers(client, "outbox-stale@example.com")
    payload, _ = start_plan(client, auth)
    goal_id = payload["goal_id"]
    _, action = preview(client, auth, goal_id)
    queued = confirm(client, auth, action)
    client.patch(f"/api/goals/{goal_id}", headers=auth, json={"title": "Different goal"})
    assert move(client, auth, queued, "dispatch").status_code == 409
    _, action = preview(client, auth, goal_id)
    queued = confirm(client, auth, action)
    with SessionLocal() as db:
        db.get(ExternalAction, queued["id"]).expires_at = outbox.now() - timedelta(seconds=1)
        db.commit()
    assert move(client, auth, queued, "dispatch").status_code == 403
    assert provider.calls == 0


def test_retry_backoff_timeout_and_duplicate_reconciliation(client, provider):
    auth = headers(client, "outbox-retry@example.com")
    payload, _ = start_plan(client, auth)
    _, action = preview(client, auth, payload["goal_id"])
    queued = confirm(client, auth, action)
    provider.fail = adapters.NoEffectRetryable
    retry = move(client, auth, queued, "dispatch").json()
    assert retry["state"] == "queued" and retry["attempts"] == 1
    assert move(client, auth, retry, "dispatch").status_code == 409
    set_due(retry)
    provider.fail = TimeoutError
    uncertain = move(client, auth, retry, "dispatch").json()
    assert uncertain["state"] == "unknown" and provider.calls == 2
    assert move(client, auth, uncertain, "dispatch").status_code == 409
    recovered = move(client, auth, uncertain, "reconcile").json()
    assert recovered["state"] == "verified"
    duplicate = move(client, auth, uncertain, "reconcile").json()
    assert duplicate["receipt"] == recovered["receipt"] and duplicate["revision"] == recovered["revision"]
    assert provider.calls == 2
    with SessionLocal() as db:
        observed = metrics(db)
        assert observed["retry_count"] == 1
        assert observed["pending_count"] == observed["unknown_count"] == observed["failed_count"] == 0
    path = f"{ROOT}/{action['id']}/verification"
    assert client.get(path, headers=auth).json()["status"] == "verified"
    receipt = provider.result
    provider.result = adapters.ProviderReceipt(receipt.identifier, "different-content")
    assert client.get(path, headers=auth).json()["status"] == "changed"
    provider.result = adapters.ProviderReceipt("wrong-result", receipt.fingerprint)
    assert client.get(path, headers=auth).json()["status"] == "failed"
    provider.result = None
    assert client.get(path, headers=auth).json()["status"] == "unknown"


def test_concurrent_dispatch_admits_one_provider_call(client, provider, test_engine):
    if test_engine.dialect.name != "postgresql":
        pytest.skip("independent PostgreSQL transactions required")
    auth = headers(client, "outbox-race@example.com")
    payload, _ = start_plan(client, auth)
    _, action = preview(client, auth, payload["goal_id"])
    queued = confirm(client, auth, action)
    entered, release = Event(), Event()

    def wait_during_apply():
        entered.set()
        assert release.wait(10)

    provider.during_apply = wait_during_apply
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(move, client, auth, queued, "dispatch")
        try:
            assert entered.wait(10)
            assert move(client, auth, queued, "dispatch").status_code == 409
        finally:
            release.set()
        assert first.result(timeout=10).json()["state"] == "verified"
    assert provider.calls == 1


def test_revocation_during_execution_records_late_evidence(client, provider):
    auth = headers(client, "outbox-revoke@example.com")
    payload, _ = start_plan(client, auth)
    _, action = preview(client, auth, payload["goal_id"])
    queued = confirm(client, auth, action)

    def revoke():
        with SessionLocal() as db:
            row = db.get(ExternalAction, action["id"])
            outbox.stop(db, row.user_id)
            db.commit()

    provider.during_apply = revoke
    result = move(client, auth, queued, "dispatch").json()
    assert result["consent"] == "revoked"
    assert result["audit"][-1]["event"] == "verified_after_revocation"
    assert move(client, auth, result, "dispatch").status_code == 409
    assert provider.calls == 1


def test_ambiguous_local_commit_uses_lookup_only(client, provider, monkeypatch):
    auth = headers(client, "outbox-commit@example.com")
    payload, _ = start_plan(client, auth)
    _, action = preview(client, auth, payload["goal_id"])
    queued = confirm(client, auth, action)

    def uncertain(*args, **kwargs):
        raise RuntimeError("Injected lost local receipt commit")

    with monkeypatch.context() as patch:
        patch.setattr(outbox, "_finish", uncertain)
        with SessionLocal() as db, pytest.raises(RuntimeError, match="lost local receipt"):
            dispatch_ready(db)
    claimed = client.get(f"{ROOT}/{action['id']}", headers=auth).json()
    assert claimed["state"] == "dispatching" and provider.calls == 1
    assert move(client, auth, claimed, "reconcile").status_code == 409
    set_due(claimed)
    with SessionLocal() as db:
        assert dispatch_ready(db) == 0
        assert metrics(db)["unknown_count"] == 1
    unknown = client.get(f"{ROOT}/{action['id']}", headers=auth).json()
    assert unknown["state"] == "unknown"
    other = headers(client, "outbox-reconcile-other@example.com")
    assert move(client, other, unknown, "reconcile").status_code == 404
    receipt = provider.result
    provider.result = None
    assert move(client, auth, unknown, "reconcile").json()["state"] == "unknown"
    provider.result = receipt
    verified = move(client, auth, unknown, "reconcile").json()
    assert verified["state"] == "verified"
    assert move(client, auth, unknown, "reconcile").json()["receipt"] == verified["receipt"]
    assert provider.calls == 1

    _, second = preview(client, auth, payload["goal_id"])
    queued = confirm(client, auth, second)
    finish = outbox._finish

    def lose_response(*args, **kwargs):
        finish(*args, **kwargs)
        raise RuntimeError("Injected lost response after local commit")

    with monkeypatch.context() as patch:
        patch.setattr(outbox, "_finish", lose_response)
        assert move(client, auth, queued, "dispatch").status_code == 500
    stored = client.get(f"{ROOT}/{second['id']}", headers=auth).json()
    assert stored["state"] == "verified" and provider.calls == 2
    assert move(client, auth, queued, "reconcile").json()["receipt"] == stored["receipt"]


def test_task_verification_and_read_only_replan_signals(client):
    from app.models.task import Task

    auth = headers(client, "receipt-owner@example.com")
    other = headers(client, "receipt-other@example.com")
    _, run = start_plan(client, auth)
    result = workflow_transition(client, auth, run, "approve").json()
    first, second, *_ = result["result"]["evidence"]["task_ids"]
    base = f"/api/v1/workflows/{run['id']}"
    assert client.get(base + "/verification", headers=auth).json()["status"] == "verified"
    assert client.get(base + "/replan-signals", headers=other).status_code == 404
    with SessionLocal() as db:
        task = db.get(Task, first)
        task.title = "Manually edited"
        task.deadline = outbox.now() - timedelta(days=1)
        db.commit()
    check = client.get(base + "/verification", headers=auth).json()
    assert (check["status"], check["changed_task_ids"]) == ("changed", [first])
    signals = client.get(base + "/replan-signals", headers=auth).json()
    assert signals["changed_task_ids"] == signals["overdue_task_ids"] == [first]
    assert signals["needs_review"] is True
    schedule = result["result"]["schedule"]
    first_slot = next(entry for entry in schedule["entries"] if entry["task_id"] == -1)
    booked = client.post("/api/planner/schedules", headers=auth, json={
        "target_date": schedule["target_date"], "idempotency_key": str(uuid4()),
        "entries": [{"task_id": second, "start_at": first_slot["start_at"], "duration_minutes": 5}],
    })
    assert booked.status_code == 201
    conflicts = client.get(base + "/replan-signals", headers=auth).json()["conflicting_task_ids"]
    assert first in conflicts
    with SessionLocal() as db:
        db.delete(db.get(Task, second))
        db.commit()
    failed = client.get(base + "/verification", headers=auth).json()
    assert failed["status"] == "failed" and failed["missing_task_ids"] == [second]
    assert client.get(base, headers=auth).json()["revision"] == result["revision"]


def test_bounded_worker_dispatches_only_confirmed_rows(client, provider):
    auth = headers(client, "outbox-worker@example.com")
    payload, _ = start_plan(client, auth)
    _, waiting = preview(client, auth, payload["goal_id"])
    _, stale = preview(client, auth, payload["goal_id"])
    confirm(client, auth, stale)
    client.patch(f"/api/goals/{payload['goal_id']}", headers=auth, json={"title": "New goal scope"})
    _, ready = preview(client, auth, payload["goal_id"])
    confirm(client, auth, ready)
    with SessionLocal() as db:
        assert dispatch_ready(db, limit=1) == 1
        assert dispatch_ready(db, limit=1) == 1
        assert dispatch_ready(db, limit=1) == 0
    assert provider.calls == 1
    assert client.get(f"{ROOT}/{stale['id']}", headers=auth).json()["state"] == "failed"
    assert client.get(f"{ROOT}/{waiting['id']}", headers=auth).json()["state"] == "preview"


def test_worker_recovers_expired_lease_without_retrying(client, provider):
    auth = headers(client, "outbox-lease@example.com")
    payload, _ = start_plan(client, auth)
    _, ready = preview(client, auth, payload["goal_id"])
    action = confirm(client, auth, ready)
    with SessionLocal() as db:
        row = db.get(ExternalAction, action["id"])
        row.state = "dispatching"
        row.due_at = outbox.now() - timedelta(seconds=1)
        row.attempts = 1
        db.commit()
        observed = metrics(db)
        assert observed["pending_count"] == 1 and observed["oldest_pending_seconds"] >= 0
        assert dispatch_ready(db) == 0
        recovered = db.get(ExternalAction, row.id)
        assert recovered.state == "unknown"
        assert recovered.attempts == 1
    assert provider.calls == 0
