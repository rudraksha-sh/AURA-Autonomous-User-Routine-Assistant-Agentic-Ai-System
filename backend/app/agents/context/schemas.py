from dataclasses import dataclass

from app.models.goal import Goal


@dataclass(frozen=True)
class GoalContext:
    goal: Goal
    source: str = "aura.goal"
