import logging
from typing import Protocol

from openai import OpenAI
from pydantic import BaseModel, Field

from app.agents.planner.prompts import SYSTEM_PROMPT, build_goal_prompt
from app.core.config import settings
from app.models.goal import Goal
from app.schemas.ai import AIProviderStatus, GoalPlan, PlannedTask
from app.services.planner_service import generate_goal_plan as generate_rule_goal_plan


logger = logging.getLogger("aura.planner")


class ProviderGoalPlan(BaseModel):
    """Provider output schema kept separate from AURA's response metadata."""

    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    priority: str = Field(default="medium", max_length=20)
    tasks: list[PlannedTask] = Field(min_length=1, max_length=50)


class GoalPlannerProvider(Protocol):
    name: str

    def generate(self, user_goal: str) -> ProviderGoalPlan: ...


class OpenRouterGoalPlanner:
    name = "openrouter"

    def __init__(self) -> None:
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.openrouter_api_key,
            timeout=settings.ai_timeout_seconds,
            max_retries=0,
        )

    def generate(self, user_goal: str) -> ProviderGoalPlan:
        response = self.client.chat.completions.parse(
            model=settings.ai_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_goal_prompt(user_goal)},
            ],
            response_format=ProviderGoalPlan,
        )
        parsed = response.choices[0].message.parsed
        if parsed is None:
            raise ValueError("AI provider returned no structured plan")
        return parsed


def provider_status() -> AIProviderStatus:
    configured = settings.ai_provider == "openrouter" and bool(settings.openrouter_api_key.strip())
    return AIProviderStatus(
        provider="openrouter" if settings.ai_provider == "openrouter" else "deterministic",
        configured=configured,
    )


def _load_provider() -> GoalPlannerProvider | None:
    if not provider_status().configured:
        return None
    return OpenRouterGoalPlanner()


def _rule_based_plan(user_goal: str) -> GoalPlan:
    # This uses fixed templates; it does not interpret arbitrary natural language.
    title = user_goal.strip()[:255]
    goal = Goal(id=0, title=title, description=None, status="active", priority="medium")
    proposal = generate_rule_goal_plan(goal, task_count=5)
    return GoalPlan(
        title=title,
        description="A deterministic template plan. The request was not interpreted by a language model.",
        priority="medium",
        tasks=[PlannedTask(
            title=task.title,
            description=task.description,
            priority=task.priority,
            estimated_minutes=task.estimated_minutes,
            position=task.position,
        ) for task in proposal.tasks],
        generation_mode="rule_based",
    )


def generate_goal_plan(user_goal: str, *, use_ai: bool = True) -> GoalPlan:
    try:
        provider = _load_provider() if use_ai else None
        if provider is None:
            return _rule_based_plan(user_goal)
        plan = provider.generate(user_goal)
        return GoalPlan(**plan.model_dump(), generation_mode="openrouter")
    except Exception as exc:
        # Keep provider exceptions and possible credential details out of API responses/logs.
        logger.warning("Planner provider failed (%s); using deterministic templates", type(exc).__name__)
        return _rule_based_plan(user_goal)
