SYSTEM_PROMPT = """
You are AURA's goal planning engine.

Convert a user's goal into a practical execution plan.

Rules:
1. Break the goal into concrete, actionable tasks.
2. Tasks must be ordered logically.
3. Prefer small, independently executable tasks.
4. Estimate realistic effort in minutes.
5. Assign task priority as low, medium, or high.
6. Do not invent external facts.
7. Do not claim that any task has already been completed.
8. Return only the requested structured output.
"""


def build_goal_prompt(goal: str) -> str:
    return f"""
Create an execution plan for this user goal:

{goal}

Produce:
- a concise goal title
- a goal description
- an overall priority
- an ordered list of actionable tasks
- estimated effort for every task
- optional deadline offsets in days when appropriate
"""