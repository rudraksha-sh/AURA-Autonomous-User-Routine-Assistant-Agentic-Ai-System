from sqlalchemy.orm import Session

from app.agents.context.agent import load_goal
from app.agents.context.retrieval import check_versions
from app.agents.replanning.agent import goal_version
from app.schemas.planner import PlanSaveRequest
from app.services.planner_service import stage_goal_tasks
from app.tools.recovery import snapshot_task


def create_reviewed_tasks(
    db: Session, user_id: int, goal_id: int, version: str, request: PlanSaveRequest,
    sources: list[dict] | None = None,
) -> dict[str, str]:
    validate_reviewed_context(db, user_id, goal_id, version, sources or [])
    tasks = stage_goal_tasks(db, goal_id, request.tasks)
    db.flush()
    return {str(task.id): snapshot_task(task) for task in tasks}


def validate_reviewed_context(db: Session, user_id: int, goal_id: int, version: str, sources: list[dict]) -> None:
    goal = load_goal(db, user_id, goal_id, lock=True).goal
    if goal_version(goal) != version:
        raise ValueError("The goal changed after the preview. Start a new workflow.")

    check_versions(db, user_id, sources)
