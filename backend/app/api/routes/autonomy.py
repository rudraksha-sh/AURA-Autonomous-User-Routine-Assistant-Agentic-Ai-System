from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.agents.context.agent import load_goal
from app.agents.execution import outbox
from app.agents.execution.policies import CONSENT_VERSION
from app.api.routes.workflows import limit_mutation
from app.core.security import get_current_user_id
from app.db.session import get_db
from app.models.autonomy import AutonomyGrant
from app.schemas.autonomy import GrantCreate, GrantResponse, GrantTransition

router = APIRouter(prefix="/api/v1/autonomy", tags=["Autonomous mode"])
mutations = [Depends(limit_mutation)]


def grant_view(grant: AutonomyGrant) -> GrantResponse:
    status = grant.status
    if status != "revoked":
        if grant.consent_version != CONSENT_VERSION:
            status = "consent_required"
        elif grant.expires_at.replace(tzinfo=grant.expires_at.tzinfo or timezone.utc) <= datetime.now(timezone.utc):
            status = "expired"
        elif not grant.runs_remaining:
            status = "exhausted"
    return GrantResponse.model_validate(grant).model_copy(update={"status": status})


@router.get("/grants", response_model=list[GrantResponse])
def list_grants(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    grants = db.scalars(select(AutonomyGrant).where(AutonomyGrant.user_id == user_id)
                        .order_by(AutonomyGrant.created_at.desc(), AutonomyGrant.id.desc()).limit(50))
    return [grant_view(grant) for grant in grants]


@router.post("/grants", status_code=201, response_model=GrantResponse, dependencies=mutations)
def create_grant(body: GrantCreate, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    if body.consent_version != CONSENT_VERSION:
        raise HTTPException(409, "Review the current autonomous mode consent terms.")
    try:
        load_goal(db, user_id, body.goal_id)
    except LookupError as exc:
        raise HTTPException(404, "Goal not found") from exc
    grant = AutonomyGrant(
        id=str(uuid4()), user_id=user_id, goal_id=body.goal_id, operation=body.operation,
        consent_version=body.consent_version, status="active", runs_remaining=body.run_limit,
        task_limit=body.task_limit, expires_at=datetime.now(timezone.utc) + timedelta(minutes=body.duration_minutes),
    )
    db.add(grant)
    db.commit()
    return grant_view(grant)


@router.post("/grants/{grant_id}/transition", response_model=GrantResponse, dependencies=mutations)
def transition_grant(grant_id: UUID, body: GrantTransition, user_id: int = Depends(get_current_user_id),
                     db: Session = Depends(get_db)):
    query = select(AutonomyGrant).where(AutonomyGrant.id == str(grant_id), AutonomyGrant.user_id == user_id)
    grant = db.scalar(query.with_for_update())
    if grant is None:
        raise HTTPException(404, "Grant not found")
    before = grant.status
    view = grant_view(grant)
    if body.operation == "revoke":
        after = "revoked"
    elif body.operation == "pause" and view.status == "active":
        after = "paused"
    elif body.operation == "resume" and view.status == "paused":
        after = "active"
    else:
        raise HTTPException(409, "This grant cannot make that transition.")
    changed = db.execute(update(AutonomyGrant).where(
        AutonomyGrant.id == grant.id, AutonomyGrant.user_id == user_id, AutonomyGrant.status == before,
    ).values(status=after))
    if changed.rowcount != 1:
        raise HTTPException(409, "This grant changed. Refresh and retry.")
    db.commit()
    return grant_view(grant)


@router.post("/stop", status_code=204, dependencies=mutations)
def emergency_stop(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    db.execute(update(AutonomyGrant).where(
        AutonomyGrant.user_id == user_id, AutonomyGrant.status != "revoked",
    ).values(status="revoked"))
    outbox.stop(db, user_id)
    db.commit()
