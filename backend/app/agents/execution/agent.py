from uuid import UUID

from sqlalchemy.orm import Session

from app.agents.memory.agent import check_memory_versions
from app.agents.execution.policies import consume_grant
from app.agents.execution.schemas import CREATE_GOAL_TASKS
from app.schemas.planner import PlanSaveRequest
from app.tools.database import create_reviewed_tasks, validate_reviewed_context
from app.agents.replanning.agent import apply_reconciliation, lock_replan_parent


def execute_plan(db: Session, state) -> tuple[dict[str, str], dict[str, str] | None]:
    if state["permitted_scopes"] != [CREATE_GOAL_TASKS]:
        raise PermissionError("Task creation is outside this workflow's scope")
    approval = state.get("approval_status")
    grant_id = state.get("grant_id")
    if approval == "grant_required" and grant_id:
        consume_grant(db, grant_id, state["user_id"], state["goal_id"], len(state["plan"]["tasks"]))
    elif approval != "approved" or grant_id:
        raise PermissionError("Task creation requires explicit workflow approval")

    request = PlanSaveRequest(idempotency_key=UUID(state["run_id"]), tasks=state["plan"]["tasks"])
    check_memory_versions(db, state["user_id"], state.get("context_snapshot", {}).get("memory_versions", {}))
    context = state.get("evidence", {}).get("context", {})
    if state.get("previous_run_id"):
        reviewed = state.get("reconciliation")
        if not reviewed:
            raise ValueError("This replan needs a new preview before approval.")
        parent = lock_replan_parent(db, state["user_id"], state["goal_id"], reviewed)
        validate_reviewed_context(db, state["user_id"], state["goal_id"], state["goal_version"],
                                  context.get("sources", []))
        return apply_reconciliation(db, parent, state["run_id"], reviewed, request.tasks)
    return create_reviewed_tasks(
        db, state["user_id"], state["goal_id"], state["goal_version"], request,
        context.get("sources", []),
    ), None
