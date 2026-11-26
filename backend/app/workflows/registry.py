import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from langgraph.types import Command
from langsmith import tracing_context
from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from app.agents.context.agent import load_goal
from app.agents.context.schemas import PlanningSnapshot
from app.agents.supervisor.schemas import GRAPH_STEP_LIMIT
from app.models.workflow import WorkflowRun
from app.tools.recovery import remove_unchanged_workflow_tasks
from app.workflows.checkpoints import TransactionJournal
from app.workflows.graph import build_graph
from app.workflows.state import Decision, WorkflowState

PUBLIC_FIELDS = ("plan", "schedule", "capacity", "comparison", "simulation", "trace", "approval_status", "evidence")
logger = logging.getLogger("aura.workflow")


class WorkflowConflict(Exception):
    pass


def owned_run(db: Session, user_id: int, run_id: UUID) -> WorkflowRun:
    row = db.scalar(select(WorkflowRun).where(WorkflowRun.id == str(run_id), WorkflowRun.user_id == user_id))
    if row is None:
        raise LookupError("Workflow not found")
    return row


def _set_transaction_limits(db: Session) -> None:
    if db.get_bind().dialect.name == "postgresql":
        db.execute(text("SET LOCAL statement_timeout = '10s'"))
        db.execute(text("SET LOCAL lock_timeout = '5s'"))


def lock_revision(db: Session, row: WorkflowRun, expected_revision: int) -> None:
    if row.revision != expected_revision:
        raise WorkflowConflict("Workflow changed. Refresh before retrying.")
    _set_transaction_limits(db)
    changed = db.execute(update(WorkflowRun).where(
        WorkflowRun.id == row.id, WorkflowRun.user_id == row.user_id,
        WorkflowRun.revision == expected_revision,
    ).values(revision=expected_revision + 1))
    if changed.rowcount != 1:
        raise WorkflowConflict("Workflow changed. Refresh before retrying.")


def _compatible_context(values: WorkflowState, row: WorkflowRun) -> bool:
    evidence = values["evidence"]
    stored_evidence = row.result["evidence"]
    if "context_snapshot" not in values:
        # Legacy goal-only journals have no context in either durable representation.
        return "context" not in evidence and "context" not in stored_evidence
    preview = evidence.get("context")
    if not isinstance(preview, dict) or preview.get("schema_version") != 1:
        return False
    snapshot = PlanningSnapshot.model_validate(values["context_snapshot"])
    return (
        snapshot.goal.id == row.goal_id
        and snapshot.goal_version == values["goal_version"]
        and snapshot.retrieval.model_dump(mode="json") == preview == stored_evidence.get("context")
        and values["context_snapshot"]["retrieval"] == preview
    )


def _invoke(db: Session, row: WorkflowRun, input_value: WorkflowState | Command) -> None:
    config = {"configurable": {"thread_id": row.id}, "recursion_limit": GRAPH_STEP_LIMIT}
    if isinstance(input_value, Command):
        try:
            saver = TransactionJournal(row.checkpoint)
            graph = build_graph(db, saver)
            snapshot = graph.get_state(config)
            values = snapshot.values
            valid = (
                snapshot.next == ("approval",) and bool(snapshot.interrupts)
                and values.get("run_id") == values.get("thread_id") == row.id
                and values.get("user_id") == row.user_id
                and values.get("goal_id") == row.goal_id
                and _compatible_context(values, row)
            )
        except Exception as exc:
            # LangGraph and its serializers can raise different errors for invalid journals.
            logger.warning("Checkpoint replay failed for workflow %s (%s)", row.id, type(exc).__name__)
            valid = False
        if not valid:
            raise WorkflowConflict("This workflow's approval checkpoint is unavailable. Cancel it and preview a new plan.")
    else:
        saver = TransactionJournal()
        graph = build_graph(db, saver)
    with tracing_context(enabled=False):
        result = graph.invoke(input_value, config, durability="sync")
    row.status = "awaiting_approval" if result.get("__interrupt__") else result["status"]
    row.checkpoint = saver.journal if row.status == "awaiting_approval" else []
    row.result = {
        **{key: result[key] for key in PUBLIC_FIELDS if key in result},
        "_request_hash": row.result["_request_hash"],
    }


def request_matches(row: WorkflowRun, state: WorkflowState) -> bool:
    return row.result.get("_request_hash") == _request_hash(state)


def _request_hash(state: WorkflowState) -> str:
    payload = json.dumps(state, sort_keys=True, ensure_ascii=True).encode()
    return hashlib.sha256(payload).hexdigest()


def start(db: Session, user_id: int, run_id: UUID, state: WorkflowState) -> WorkflowRun:
    _set_transaction_limits(db)
    if state.get("goal_id") is not None:
        load_goal(db, user_id, state["goal_id"])
    row = WorkflowRun(
        id=str(run_id), user_id=user_id, goal_id=state.get("goal_id"),
        status="starting", checkpoint=[], result={"_request_hash": _request_hash(state)}, revision=0,
    )
    db.add(row)
    db.flush()
    _invoke(db, row, {
        **state, "user_id": user_id, "run_id": row.id, "thread_id": row.id,
    })
    db.commit()
    return row


def transition(db: Session, row: WorkflowRun, operation: Decision | str, revision: int) -> WorkflowRun:
    if row.status == "paused" and operation not in ("resume", "cancel"):
        raise WorkflowConflict("Resume this workflow before making a decision.")
    if operation == "pause" and row.status == "paused":
        raise WorkflowConflict("This workflow is already paused.")
    if row.status not in ("awaiting_approval", "paused"):
        raise WorkflowConflict("This workflow already reached a terminal state.")
    if operation == "resume" and row.status != "paused":
        raise WorkflowConflict("Only paused workflows can be resumed.")
    if row.goal_id is None and operation != "cancel":
        raise WorkflowConflict("The original goal is no longer available.")

    created = row.created_at.replace(tzinfo=row.created_at.tzinfo or timezone.utc)
    if operation == "approve" and datetime.now(timezone.utc) - created >= timedelta(hours=24):
        raise WorkflowConflict("This approval expired. Preview a new plan.")
    if operation == "pause" and row.revision >= 24:
        raise WorkflowConflict("This workflow reached its pause limit. Approve, reject, or cancel it.")
    lock_revision(db, row, revision)
    if operation == "cancel":
        row.status = "cancelled"
        row.checkpoint = []
        row.result = {**row.result, "approval_status": "cancelled", "trace": [*row.result["trace"], {
            "agent": "approval", "outcome": "cancelled", "at": datetime.now(timezone.utc).isoformat()
        }]}
        db.commit()
    elif operation in ("pause", "resume"):
        row.status = "paused" if operation == "pause" else "awaiting_approval"
        row.result = {**row.result, "trace": [*row.result["trace"], {
            "agent": "supervisor", "outcome": row.status, "at": datetime.now(timezone.utc).isoformat()
        }]}
        db.commit()
    else:
        prior_trace = row.result["trace"]
        graph_trace_length = sum(item["outcome"] not in ("paused", "awaiting_approval") for item in prior_trace)
        _invoke(db, row, Command(resume=operation))
        row.result = {**row.result, "trace": [*prior_trace, *row.result["trace"][graph_trace_length:]]}
        db.commit()
    return row


def undo(db: Session, row: WorkflowRun, revision: int) -> WorkflowRun:
    evidence = row.result.get("evidence", {})
    snapshots = evidence.get("_task_snapshots")
    if row.status != "completed" or row.goal_id is None or not snapshots or evidence.get("reconciled") or row.result.get("_replan_run_id"):
        raise WorkflowConflict("This workflow has no reversible task creation.")
    lock_revision(db, row, revision)
    remove_unchanged_workflow_tasks(db, row.user_id, row.goal_id, snapshots)
    row.status = "undone"
    row.result = {**row.result, "trace": [*row.result["trace"], {
        "agent": "execution", "outcome": "undone", "at": datetime.now(timezone.utc).isoformat(),
    }]}
    db.commit()
    return row
