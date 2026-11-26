"""Single-action outbox with compare-and-swap claims and conservative recovery."""
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.agents.context.agent import load_goal
from app.agents.execution import adapters
from app.agents.replanning.agent import goal_version
from app.models.external_action import ExternalAction

MAX_ATTEMPTS = 3
PROVIDER_TIMEOUT = 5
LEASE = timedelta(seconds=60)


def now():
    return datetime.now(timezone.utc)


def _utc(value):
    return value.replace(tzinfo=value.tzinfo or timezone.utc)


def _digest(values):
    return hashlib.sha256(json.dumps(values, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _scope(row):
    return f"owner:{row.user_id}/goal:{row.goal_id}"


def _audit(outcome):
    return {"event": outcome, "at": now().isoformat()}


def _query(user_id, action_id):
    return select(ExternalAction).where(ExternalAction.id == action_id, ExternalAction.user_id == user_id)


def owned(db: Session, user_id: int, action_id: str) -> ExternalAction:
    row = db.scalar(_query(user_id, action_id).execution_options(populate_existing=True))
    if row is None:
        raise LookupError("External action not found.")
    return row


def _change(db, row, revision, event, **changes):
    result = db.execute(update(ExternalAction).where(
        ExternalAction.id == row.id, ExternalAction.user_id == row.user_id, ExternalAction.revision == revision,
    ).values(revision=revision + 1, audit=[*row.audit, _audit(event)], **changes))
    if result.rowcount != 1:
        raise ValueError("External action changed. Refresh before retrying.")


def preview(db, user_id, request_id, goal_id, start_at, duration):
    goal = load_goal(db, user_id, goal_id).goal
    payload = {"start_at": start_at.astimezone(timezone.utc).isoformat(), "duration_minutes": duration}
    scope = [user_id, goal_id, adapters.PROVIDER, adapters.OPERATION, payload]
    fingerprint = _digest(scope)
    row = ExternalAction(
        id=str(uuid4()), user_id=user_id, request_id=request_id, goal_id=goal_id,
        provider=adapters.PROVIDER, operation=adapters.OPERATION, goal_version=goal_version(goal),
        fingerprint=fingerprint, payload=payload, state="preview", consent="off", revision=0,
        attempts=0, due_at=now(), expires_at=now() + timedelta(minutes=15), receipt=None,
        audit=[_audit("previewed")],
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(ExternalAction).where(
            ExternalAction.user_id == user_id, ExternalAction.request_id == request_id,
        ))
        if existing is None or existing.fingerprint != fingerprint:
            raise ValueError("This request ID was used for another action.") from None
        return existing
    return row


def _authorize(db, row, *, lock=False):
    if row.provider != adapters.PROVIDER or row.operation != adapters.OPERATION:
        raise PermissionError("External action is outside the allowlist.")
    if (row.goal_id is None or _utc(row.expires_at) <= now()
            or datetime.fromisoformat(row.payload["start_at"]) <= now()):
        raise PermissionError("External action scope or approval has expired.")
    if row.fingerprint != _digest([row.user_id, row.goal_id, row.provider, row.operation, row.payload]):
        raise PermissionError("External action payload changed.")
    if goal_version(load_goal(db, row.user_id, row.goal_id, lock=lock).goal) != row.goal_version:
        raise ValueError("The goal changed. Preview this action again.")


def transition(db, row, revision, operation, *, consent_version=None, fingerprint=None):
    if row.revision != revision:
        raise ValueError("External action changed. Refresh before retrying.")
    if operation == "confirm":
        if (row.state != "preview" or row.consent != "off" or consent_version != adapters.CONSENT_VERSION
                or fingerprint != row.fingerprint):
            raise PermissionError("Current action scope and explicit confirmation are required.")
        _authorize(db, row, lock=True)
        _change(db, row, revision, "confirmed", state="queued", consent="active")
    elif operation == "pause" and row.consent == "active" and row.state == "queued":
        _change(db, row, revision, "paused", consent="paused")
    elif operation == "resume" and row.consent == "paused" and row.state == "queued":
        _authorize(db, row, lock=True)
        _change(db, row, revision, "resumed", consent="active")
    elif operation == "revoke" and row.consent != "revoked":
        _change(db, row, revision, "revoked", consent="revoked")
    else:
        raise ValueError("This action cannot make that transition.")
    db.commit()
    return row


def stop(db, user_id):
    # Optimistic claims and stop race on the same rows. Incrementing the revision
    # prevents a stale worker from authorizing another provider write.
    rows = db.scalars(select(ExternalAction).where(
        ExternalAction.user_id == user_id, ExternalAction.consent.in_(("off", "active", "paused")),
        ExternalAction.state.in_(("preview", "queued", "dispatching")),
    ).order_by(ExternalAction.id).with_for_update()).all()
    for row in rows:
        _change(db, row, row.revision, "emergency_stop", consent="revoked")


def _finish(db, user_id, action_id, claimed_revision, outcome, receipt=None):
    row = owned(db, user_id, action_id)
    if row.state != "dispatching":
        return row
    if outcome == "retry":
        outcome = "queued" if row.revision == claimed_revision and row.attempts < MAX_ATTEMPTS else "failed"
    changes = {"state": outcome}
    if outcome == "queued":
        changes["due_at"] = now() + timedelta(seconds=2 ** row.attempts)
    if receipt:
        changes["receipt"] = receipt
    event = "verified_after_revocation" if outcome == "verified" and row.consent == "revoked" else outcome
    _change(db, row, row.revision, event, **changes)
    db.commit()
    return row


def recover_stale_leases(db: Session, limit: int = 100) -> int:
    """Mark expired dispatch leases uncertain so they require provider lookup."""
    expired = db.scalars(select(ExternalAction).where(
        ExternalAction.state == "dispatching",
        ExternalAction.due_at <= now(),
    ).order_by(ExternalAction.due_at, ExternalAction.id).limit(max(1, min(limit, 500)))
      .with_for_update(skip_locked=True)).all()
    for row in expired:
        _change(db, row, row.revision, "lease_expired", state="unknown")
    db.commit()
    return len(expired)


def _validated_receipt(result, expected):
    if (not isinstance(result, adapters.ProviderReceipt) or result.fingerprint != expected
            or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,120}", result.identifier)):
        return None
    return {"provider_id": result.identifier, "fingerprint": expected, "observed_at": now().isoformat()}


def dispatch(db, row, revision, *, retire_invalid=False):
    if revision != row.revision or row.state != "queued" or row.consent != "active":
        raise ValueError("External action is not available for dispatch.")
    if _utc(row.due_at) > now():
        raise ValueError("Retry backoff is still active.")
    try:
        _authorize(db, row, lock=True)
    except (PermissionError, LookupError, ValueError):
        if not retire_invalid:
            raise
        _change(db, row, revision, "scope_invalid", state="failed", consent="revoked")
        db.commit()
        return row
    adapter = adapters.get_adapter(row.provider, row.operation)
    if adapter is None:
        raise PermissionError("No sandbox provider adapter is available.")
    user_id, action_id = row.user_id, row.id
    claimed_revision = revision + 1
    _change(db, row, revision, "claimed", state="dispatching", attempts=row.attempts + 1, due_at=now() + LEASE)
    db.commit()  # A claim must be durable before any provider call.
    row = owned(db, user_id, action_id)
    if row.revision != claimed_revision or row.consent != "active":
        return _finish(db, user_id, action_id, claimed_revision, "failed")
    try:
        _authorize(db, row)
    except (PermissionError, LookupError, ValueError):
        return _finish(db, user_id, action_id, claimed_revision, "failed")
    try:
        result = adapter.apply(key=row.id, resource=_scope(row), payload=dict(row.payload),
                               fingerprint=row.fingerprint, timeout_seconds=PROVIDER_TIMEOUT)
        receipt = _validated_receipt(result, row.fingerprint)
    except adapters.NoEffectRetryable:
        return _finish(db, user_id, action_id, claimed_revision, "retry")
    except Exception:
        return _finish(db, user_id, action_id, claimed_revision, "unknown")
    return _finish(db, user_id, action_id, claimed_revision, "verified" if receipt else "unknown", receipt)


def reconcile(db, row, revision):
    if row.state in ("verified", "failed"):
        return row
    if row.revision != revision or not (row.state == "unknown" or (
        row.state == "dispatching" and _utc(row.due_at) <= now()
    )):
        raise ValueError("External action is not available for reconciliation.")
    adapter = adapters.get_adapter(row.provider, row.operation)
    if adapter is None or row.goal_id is None or row.operation != adapters.OPERATION or row.provider != adapters.PROVIDER:
        raise PermissionError("Provider reconciliation is unavailable.")
    try:
        receipt = _validated_receipt(adapter.lookup(key=row.id, resource=_scope(row), timeout_seconds=PROVIDER_TIMEOUT), row.fingerprint)
    except Exception:
        receipt = None
    if receipt:
        _change(db, row, revision, "reconciled", state="verified", receipt=receipt)
    elif row.state != "unknown":
        _change(db, row, revision, "unknown", state="unknown")
    db.commit()
    return row


def verify_provider(row):
    if row.state == "failed":
        return {"status": "failed", "receipt": row.receipt}
    adapter = adapters.get_adapter(row.provider, row.operation)
    if (adapter is None or row.goal_id is None or not row.receipt
            or row.provider != adapters.PROVIDER or row.operation != adapters.OPERATION
            or row.consent == "revoked"):
        return {"status": "unknown", "receipt": row.receipt}
    try:
        observed = adapter.lookup(key=row.id, resource=_scope(row), timeout_seconds=PROVIDER_TIMEOUT)
    except Exception:
        observed = None
    if not isinstance(observed, adapters.ProviderReceipt):
        status = "unknown"
    elif observed.identifier != row.receipt["provider_id"]:
        status = "failed"
    else:
        status = "verified" if observed.fingerprint == row.receipt["fingerprint"] else "changed"
    return {"status": status, "receipt": row.receipt}



def receive_callback(db, *, user_id: int, action_id: str, callback_id: str, fingerprint: str, provider_id: str):
    """Deduplicate an authenticated provider callback against the user/action scope."""
    import re

    row = owned(db, user_id, action_id)
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,120}", callback_id) or row.fingerprint != fingerprint:
        raise PermissionError("Provider callback is outside the confirmed action scope.")
    event_key = f"callback:{callback_id}"
    if any(item.get("event") == event_key for item in row.audit):
        return row
    if row.state not in ("dispatching", "unknown", "verified"):
        raise ValueError("Provider callback arrived outside an active action.")
    receipt = {"provider_id": provider_id, "fingerprint": fingerprint, "callback_id": callback_id,
               "observed_at": now().isoformat()}
    _change(db, row, row.revision, event_key, state="verified", receipt=receipt)
    db.commit()
    return row


def compensate(db, row, revision: int, adapter):
    """Call an adapter's explicit compensation port after a confirmed effect."""
    if row.revision != revision or row.state != "verified" or not row.receipt:
        raise ValueError("Only a verified action can be compensated.")
    undo = getattr(adapter, "compensate", None)
    if not callable(undo):
        raise PermissionError("This provider does not support compensation.")
    result = undo(key=row.id, resource=_scope(row), receipt=dict(row.receipt), timeout_seconds=PROVIDER_TIMEOUT)
    if result != row.fingerprint:
        raise ValueError("Provider compensation could not be verified.")
    _change(db, row, revision, "compensated", state="failed")
    db.commit()
    return row
