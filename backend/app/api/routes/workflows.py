from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from app.agents.replanning.agent import detect_replan_signals
from app.agents.verification.agent import verify_tasks
from app.agents.verification.schemas import VerificationReceipt
from app.core.rate_limit_dependencies import workflow_limiter
from app.core.security import get_current_user_id
from app.db.session import get_db
from app.models.workflow import WorkflowRun
from app.schemas.workflow import PlanStart, TraceEvent, UndoRequest, WorkflowResponse, WorkflowStart, WorkflowTransition
from app.workflows import registry

router = APIRouter(prefix="/api/v1/workflows", tags=["Agent workflows"])


def rollback_database_error(db: Session, error: DBAPIError) -> None:
    db.rollback()
    if getattr(error.orig, "sqlstate", None) in {"55P03", "57014", "40001", "40P01"}:
        raise HTTPException(
            503, "The workflow database is busy. Retry the same request.",
            headers={"Retry-After": "1"},
        ) from error


def limit_mutation(user_id: int = Depends(get_current_user_id)) -> None:
    if not workflow_limiter.allow(f"workflow:{user_id}"):
        raise HTTPException(429, "Too many workflow requests", headers={"Retry-After": "60"})


@router.post("", response_model=WorkflowResponse, status_code=201, dependencies=[Depends(limit_mutation)])
def start_workflow(body: WorkflowStart, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    state = ({"intent": body.intent, "goal_id": body.goal_id, "target_date": body.target_date.isoformat(),
              **({"include_calendar": True} if body.include_calendar else {}),
              "task_count": body.task_count, "grant_id": str(body.grant_id) if body.grant_id else None,
              "previous_run_id": str(body.previous_run_id) if body.previous_run_id else None}
             if isinstance(body, PlanStart)
             else {"intent": body.intent, "scenario": body.scenario.model_dump(mode="json")})
    try:
        return registry.start(db, user_id, body.run_id, state)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(422, "The proposal could not be validated.") from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        try:
            existing = registry.owned_run(db, user_id, body.run_id)
            if not registry.request_matches(existing, state):
                raise HTTPException(409, "This workflow ID was used with different inputs.")
            return existing
        except LookupError:
            raise HTTPException(409, "Unable to start workflow with this ID.") from exc
    except DBAPIError as exc:
        rollback_database_error(db, exc)
        raise


@router.get("", response_model=list[WorkflowResponse])
def list_workflows(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    return list(db.scalars(select(WorkflowRun).where(WorkflowRun.user_id == user_id)
                           .order_by(WorkflowRun.created_at.desc(), WorkflowRun.id.desc()).limit(20)))


@router.get("/{run_id}", response_model=WorkflowResponse)
def get_workflow(run_id: UUID, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    try:
        return registry.owned_run(db, user_id, run_id)
    except LookupError as exc:
        raise HTTPException(404, "Workflow not found") from exc


@router.post("/{run_id}/transition", response_model=WorkflowResponse, dependencies=[Depends(limit_mutation)])
def transition_workflow(run_id: UUID, body: WorkflowTransition, user_id: int = Depends(get_current_user_id),
                        db: Session = Depends(get_db)):
    try:
        row = get_workflow(run_id, user_id, db)
        return registry.transition(db, row, body.operation, body.revision)
    except LookupError as exc:
        raise HTTPException(404, "Goal not found") from exc
    except ValidationError as exc:
        raise HTTPException(409, "The proposal expired or is invalid. Start a new workflow.") from exc
    except (ValueError, registry.WorkflowConflict) as exc:
        db.rollback()
        raise HTTPException(409, str(exc)) from exc
    except DBAPIError as exc:
        rollback_database_error(db, exc)
        raise


@router.get("/{run_id}/audit", response_model=list[TraceEvent])
def workflow_audit(run_id: UUID, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    return get_workflow(run_id, user_id, db).result["trace"]


@router.get("/{run_id}/verification", response_model=VerificationReceipt)
def workflow_verification(run_id: UUID, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    row = get_workflow(run_id, user_id, db)
    evidence = row.result.get("evidence", {})
    if not evidence.get("task_ids"):
        raise HTTPException(409, "This workflow has no execution receipt.")
    return verify_tasks(db, user_id, row.goal_id, evidence["task_ids"], evidence.get("_task_snapshots"))


@router.post("/{run_id}/undo", response_model=WorkflowResponse, dependencies=[Depends(limit_mutation)])
def undo_workflow(run_id: UUID, body: UndoRequest, user_id: int = Depends(get_current_user_id),
                  db: Session = Depends(get_db)):
    try:
        row = get_workflow(run_id, user_id, db)
        return registry.undo(db, row, body.revision)
    except (ValueError, registry.WorkflowConflict) as exc:
        raise HTTPException(409, str(exc)) from exc
    except DBAPIError as exc:
        rollback_database_error(db, exc)
        raise


@router.get("/{run_id}/replan-signals")
def replan_signals(run_id: UUID, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    row = get_workflow(run_id, user_id, db)
    if row.status != "completed" or row.goal_id is None or row.result.get("_replan_run_id"):
        return {"changed_task_ids": [], "missing_task_ids": [], "overdue_task_ids": [],
                "conflicting_task_ids": [], "needs_review": False}
    return detect_replan_signals(db, row)
