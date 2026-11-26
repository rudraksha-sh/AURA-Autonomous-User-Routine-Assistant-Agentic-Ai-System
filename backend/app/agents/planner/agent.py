from app.agents.context.schemas import PlanningSnapshot
from app.agents.planner.schemas import PlanRequest, PlanResponse
from app.services.planner_service import generate_goal_plan


def plan_goal(context: PlanningSnapshot, request: PlanRequest) -> PlanResponse:
    plan = generate_goal_plan(context.goal, request.task_count)
    if context.retrieval.sources:
        gather_task = plan.tasks[1]
        gather_task.description = f"{gather_task.description} Review the related sources in the context preview."
    if context.memory_versions:
        gather_task = plan.tasks[1]
        gather_task.description = f"{gather_task.description} Review your saved planning memories."
    return plan
