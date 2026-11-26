from operator import add
from typing import Annotated, Literal, TypedDict

Decision = Literal["approve", "reject", "cancel"]


class WorkflowState(TypedDict, total=False):
    user_id: int
    run_id: str
    thread_id: str
    goal_id: int
    grant_id: str | None
    previous_run_id: str | None
    comparison: dict
    reconciliation: dict
    intent: Literal["plan_goal", "simulate"]
    permitted_scopes: list[str]
    target_date: str
    task_count: int
    include_calendar: bool
    proposed_actions: list[str]
    plan: dict
    goal_version: str
    context_snapshot: dict
    schedule: dict
    capacity: dict
    scenario: dict
    simulation: dict
    decision: Decision
    approval_status: str
    status: str
    evidence: dict
    errors: list[str]
    trace: Annotated[list[dict[str, str]], add]
