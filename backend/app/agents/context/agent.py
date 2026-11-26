from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.context.embeddings import EmbeddingUnavailable
from app.agents.context.retrieval import CREDENTIAL, search
from app.agents.context.schemas import ContextPreview, GoalContext, PlanningGoal, PlanningSnapshot, SourceReference
from app.agents.replanning.agent import goal_version
from app.agents.memory.agent import recall_memory_versions
from app.models.goal import Goal


def load_goal(db: Session, user_id: int, goal_id: int, *, lock: bool = False) -> GoalContext:
    query = select(Goal).where(Goal.id == goal_id, Goal.user_id == user_id)
    if lock:
        query = query.with_for_update(key_share=True).execution_options(populate_existing=True)
    goal = db.scalar(query)
    if goal is None:
        raise LookupError("Goal not found")
    return GoalContext(goal)


def collect_snapshot(db: Session, user_id: int, goal_id: int) -> PlanningSnapshot:
    goal = load_goal(db, user_id, goal_id).goal
    title = "[redacted]" if CREDENTIAL.search(goal.title) else goal.title
    description = goal.description
    if description and CREDENTIAL.search(description):
        description = "[redacted]"
    planning_goal = PlanningGoal(id=goal.id, title=title, description=description[:400] if description else None,
                                 deadline=goal.deadline)
    try:
        query = " ".join(value for value in (title, planning_goal.description) if value)
        if CREDENTIAL.search(query):
            query = "[redacted]"
        hits = search(db, user_id, query, 4, goal_id=goal_id, include_text=False)
        preview = ContextPreview(status="ready", sources=[SourceReference.model_validate(hit) for hit in hits])
    except EmbeddingUnavailable:
        preview = ContextPreview(status="unavailable", sources=[])
    return PlanningSnapshot(goal=planning_goal, goal_version=goal_version(goal), retrieval=preview,
                            memory_versions=recall_memory_versions(db, user_id))
