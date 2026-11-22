from app.agents.context.schemas import GoalContext
from app.agents.planner.schemas import PlanRequest, PlanResponse
from app.services.planner_service import generate_goal_plan


def plan_goal(context: GoalContext, request: PlanRequest) -> PlanResponse:
    return generate_goal_plan(context.goal, request.task_count)
