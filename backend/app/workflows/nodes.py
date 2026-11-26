import logging
from datetime import date, datetime, timezone

from langgraph.types import interrupt
from sqlalchemy.orm import Session

from app.agents.context.agent import collect_snapshot
from app.agents.context.schemas import PlanningSnapshot
from app.agents.execution.agent import execute_plan
from app.agents.execution.schemas import CREATE_GOAL_TASKS
from app.agents.intelligence.agent import evaluate_capacity
from app.agents.replanning.agent import compare_plans, preview_reconciliation
from app.agents.planner.agent import plan_goal
from app.agents.scheduler.agent import schedule_plan
from app.agents.simulation.agent import simulate
from app.agents.supervisor.agent import route_intent
from app.agents.verification.agent import verify_tasks
from app.schemas.daily_planner import WhatIfRequest
from app.schemas.planner import PlanRequest, PlanResponse
from app.workflows.state import WorkflowState

logger = logging.getLogger("aura.workflow")


def event(state: WorkflowState, agent: str, outcome: str = "completed") -> dict:
    logger.info("workflow_node run_id=%s agent=%s outcome=%s", state["run_id"], agent, outcome)
    return {"trace": [{
        "agent": agent, "outcome": outcome, "at": datetime.now(timezone.utc).isoformat()
    }]}


def supervise(state: WorkflowState) -> dict:
    intent = route_intent(state)
    scopes = [CREATE_GOAL_TASKS] if intent == "plan_goal" else []
    return {"permitted_scopes": scopes, **event(state, "supervisor")}


def collect_context(state: WorkflowState, db: Session) -> dict:
    snapshot = collect_snapshot(db, state["user_id"], state["goal_id"])
    return {
        "goal_version": snapshot.goal_version,
        "context_snapshot": snapshot.model_dump(mode="json"),
        "evidence": {"source": "aura.goal", "context": snapshot.retrieval.model_dump(mode="json")},
        **event(state, "context"),
    }


def plan(state: WorkflowState, db: Session) -> dict:
    snapshot = PlanningSnapshot.model_validate(state["context_snapshot"])
    proposal = plan_goal(snapshot, PlanRequest(task_count=state["task_count"]))
    return {
        "plan": proposal.model_dump(mode="json"),
        "proposed_actions": [CREATE_GOAL_TASKS],
        **event(state, "planner"),
    }


def compare(state: WorkflowState, db: Session) -> dict:
    comparison = compare_plans(db, state["user_id"], state["goal_id"], state["previous_run_id"], state["plan"])
    reviewed = preview_reconciliation(db, state["user_id"], state["goal_id"], state["previous_run_id"], state["plan"])
    return {
        "reconciliation": reviewed,
        "comparison": {
            **comparison.model_dump(mode="json"),
            "preserved_task_ids": reviewed["preserved"],
            "updated_task_ids": [int(value) for value in reviewed["updates"].values()],
            "deleted_task_ids": [value for value in reviewed["ids"] if str(value) not in reviewed["expected"]],
            "preserved_positions": reviewed["skipped"],
        },
        **event(state, "replanning"),
    }


def schedule(state: WorkflowState, db: Session) -> dict:
    preview = schedule_plan(
        db, state["user_id"], date.fromisoformat(state["target_date"]),
        PlanResponse.model_validate(state["plan"]),
        include_calendar=state.get("include_calendar", False),
        reconciliation=state.get("reconciliation"),
    )
    return {
        "schedule": preview.model_dump(mode="json"),
        "capacity": evaluate_capacity(preview).model_dump(mode="json"),
        **event(state, "scheduler"),
    }


def review(state: WorkflowState) -> dict:
    if state.get("grant_id"):
        return {
            "decision": "approve", "approval_status": "grant_required",
            **event(state, "approval", "grant_required"),
        }
    decision = interrupt({"scope": CREATE_GOAL_TASKS, "goal_id": state["goal_id"]})
    if decision not in ("approve", "reject", "cancel"):
        raise ValueError("Invalid approval decision")
    outcome = {"approve": "approved", "reject": "rejected", "cancel": "cancelled"}[decision]
    return {
        "decision": decision, "approval_status": outcome, "status": outcome,
        **event(state, "approval", outcome),
    }


def execute(state: WorkflowState, db: Session) -> dict:
    snapshots, positions = execute_plan(db, state)
    evidence = {**state["evidence"], "task_ids": [int(value) for value in snapshots], "_task_snapshots": snapshots}
    if positions is not None:
        evidence["_task_positions"] = positions
        evidence["_protected_task_ids"] = state["reconciliation"]["preserved"]
        evidence["reconciled"] = True
    if state.get("grant_id"):
        evidence["grant_id"] = state["grant_id"]
    return {"evidence": evidence, "approval_status": "grant_authorized" if state.get("grant_id") else "approved",
            **event(state, "execution")}


def verify(state: WorkflowState, db: Session) -> dict:
    receipt = verify_tasks(db, state["user_id"], state["goal_id"], state["evidence"]["task_ids"],
                           state["evidence"].get("_task_snapshots"))
    if receipt.status != "verified":
        raise RuntimeError("Local task receipt could not be verified")
    return {
        "status": "completed",
        "evidence": {**state["evidence"], **receipt.model_dump(mode="json")},
        **event(state, "verification", receipt.status),
    }


def run_simulation(state: WorkflowState, db: Session) -> dict:
    result = simulate(db, state["user_id"], WhatIfRequest.model_validate(state["scenario"]))
    return {"simulation": result.model_dump(mode="json"), "status": "completed", **event(state, "simulation")}
