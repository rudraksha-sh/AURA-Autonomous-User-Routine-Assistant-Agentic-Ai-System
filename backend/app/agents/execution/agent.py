from uuid import UUID

from sqlalchemy.orm import Session

from app.agents.execution.policies import consume_grant
from app.agents.execution.schemas import CREATE_GOAL_TASKS
from app.schemas.planner import PlanSaveRequest
from app.tools.database import create_reviewed_tasks


def execute_plan(db: Session, state) -> dict[str, str]:
    if state["permitted_scopes"] != [CREATE_GOAL_TASKS]:
        raise PermissionError("Task creation is outside this workflow's scope")
    approval = state.get("approval_status")
    grant_id = state.get("grant_id")
    if approval == "grant_required" and grant_id:
        consume_grant(db, grant_id, state["user_id"], state["goal_id"], len(state["plan"]["tasks"]))
    elif approval != "approved" or grant_id:
        raise PermissionError("Task creation requires explicit workflow approval")

    request = PlanSaveRequest(idempotency_key=UUID(state["run_id"]), tasks=state["plan"]["tasks"])
    return create_reviewed_tasks(db, state["user_id"], state["goal_id"], state["goal_version"], request)
