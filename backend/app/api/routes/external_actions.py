from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.agents.execution import adapters, outbox
from app.api.routes.workflows import limit_mutation
from app.core.security import get_current_user_id
from app.db.session import get_db
from app.models.external_action import ExternalAction

router = APIRouter(prefix="/api/v1/external-actions", tags=["External actions"])
mutations = [Depends(limit_mutation)]


class ActionPreview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    goal_id: int = Field(gt=0, le=2_147_483_647)
    provider: Literal["sandbox_calendar"]
    operation: Literal["calendar.hold.create"]
    start_at: AwareDatetime
    duration_minutes: int = Field(ge=5, le=120)


class ActionTransition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation: Literal["confirm", "pause", "resume", "revoke", "dispatch", "reconcile"]
    revision: int = Field(ge=0)
    consent_version: str | None = Field(default=None, max_length=32)
    fingerprint: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")


def _view(row):
    return {
        "id": row.id, "goal_id": row.goal_id, "provider": row.provider, "operation": row.operation,
        "payload": row.payload, "state": row.state, "consent": row.consent, "revision": row.revision,
        "attempts": row.attempts, "due_at": outbox._utc(row.due_at),
        "expires_at": outbox._utc(row.expires_at), "fingerprint": row.fingerprint,
        "adapter_available": adapters.get_adapter(row.provider, row.operation) is not None,
        "consent_version": adapters.CONSENT_VERSION, "receipt": row.receipt, "audit": row.audit,
        "effect": "Create one synthetic calendar hold for this goal after confirmation and dispatch.",
    }


def _handle(operation):
    try:
        return _view(operation())
    except LookupError:
        raise HTTPException(404, "External action or goal not found.") from None
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from None
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from None


@router.post("", status_code=201, dependencies=mutations)
def preview(body: ActionPreview, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    return _handle(lambda: outbox.preview(db, user_id, str(body.request_id), body.goal_id,
                                            body.start_at, body.duration_minutes))


@router.get("")
def list_actions(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    rows = db.scalars(select(ExternalAction).where(ExternalAction.user_id == user_id)
                      .order_by(ExternalAction.expires_at.desc(), ExternalAction.id).limit(20))
    return [_view(row) for row in rows]


@router.get("/{action_id}")
def view(action_id: UUID, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    return _handle(lambda: outbox.owned(db, user_id, str(action_id)))


@router.post("/{action_id}/transition", dependencies=mutations)
def transition(action_id: UUID, body: ActionTransition, user_id: int = Depends(get_current_user_id),
               db: Session = Depends(get_db)):
    def apply():
        row = outbox.owned(db, user_id, str(action_id))
        if body.operation == "dispatch":
            return outbox.dispatch(db, row, body.revision)
        if body.operation == "reconcile":
            return outbox.reconcile(db, row, body.revision)
        return outbox.transition(db, row, body.revision, body.operation, consent_version=body.consent_version,
                                 fingerprint=body.fingerprint)

    return _handle(apply)


@router.get("/{action_id}/verification", dependencies=mutations)
def verify(action_id: UUID, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    try:
        row = outbox.owned(db, user_id, str(action_id))
    except LookupError:
        raise HTTPException(404, "External action not found.") from None
    return outbox.verify_provider(row)
