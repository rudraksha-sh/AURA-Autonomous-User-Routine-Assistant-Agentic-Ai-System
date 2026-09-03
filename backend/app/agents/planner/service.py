from openai import OpenAI

from app.agents.planner.prompts import (
    SYSTEM_PROMPT,
    build_goal_prompt,
)
from app.core.config import settings
from app.schemas.ai import GoalPlan


client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.openrouter_api_key,
)


def generate_goal_plan(user_goal: str) -> GoalPlan:
    response = client.chat.completions.parse(
        model=settings.ai_model,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": build_goal_prompt(user_goal),
            },
        ],
        response_format=GoalPlan,
    )

    message = response.choices[0].message

    if message.parsed is None:
        raise ValueError("AI planner returned no structured plan")

    return message.parsed