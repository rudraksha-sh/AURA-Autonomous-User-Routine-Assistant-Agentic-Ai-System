import json
from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.agent_run import AgentRun
from app.models.goal import Goal
from app.models.task import Task
from app.schemas.planner import PlanResponse, PlanSaveRequest, ProposedTask


_TEMPLATES = (
    ("Clarify the outcome", "Write down what a successful result looks like and how you will measure it.", 30, "high"),
    ("Gather what you need", "List the information, materials, or access needed to make progress.", 45, "medium"),
    ("Complete the first focused step", "Choose one small, concrete action and finish it in a focused work session.", 60, "high"),
    ("Review your progress", "Compare your progress with the intended outcome and note any open questions.", 30, "medium"),
    ("Take the next practical step", "Use what you learned to complete the next useful action toward the goal.", 60, "medium"),
    ("Check and finish remaining work", "Review outstanding work, address the most important gap, and record the result.", 45, "low"),
    ("Reflect and choose what comes next", "Summarize what worked and identify a reasonable follow-up action.", 20, "low"),
    ("Confirm the outcome", "Check the result against your success measure and update the goal if needed.", 20, "low"),
)


def _safe_context(goal: Goal) -> str:
    # The description is context only; planning remains a fixed rule/template process.
    description = (goal.description or "").strip()
    if not description:
        return f"Goal: {goal.title.strip()}"
    return f"Goal: {goal.title.strip()}. Context: {description[:400]}"


def generate_goal_plan(goal: Goal, task_count: int = 5, *, today: date | None = None) -> PlanResponse:
    if not 3 <= task_count <= 8:
        raise ValueError("task_count must be between 3 and 8")

    current_day = today or datetime.now(timezone.utc).date()
    due_date = goal.deadline.date() if goal.deadline else None
    if due_date is not None and due_date < current_day:
        due_date = None
    span = max((due_date - current_day).days, 1) if due_date else 0
    context = _safe_context(goal)
    tasks: list[ProposedTask] = []
    for index, (title, instruction, estimate, priority) in enumerate(_TEMPLATES[:task_count], start=1):
        deadline = None
        if due_date:
            day_offset = max(1, round(span * index / task_count))
            suggested_day = min(current_day + timedelta(days=day_offset), due_date)
            deadline = datetime.combine(suggested_day, time(17, 0), tzinfo=timezone.utc)
        tasks.append(ProposedTask(
            title=f"{title}: {goal.title.strip()[:150]}",
            description=f"{instruction} {context}",
            priority=priority,
            estimated_minutes=estimate,
            deadline=deadline,
            position=index,
        ))
    return PlanResponse(
        generation_mode="rule_based",
        goal_id=goal.id,
        goal_title=goal.title,
        tasks=tasks,
    )


def save_goal_plan(
    db: Session,
    *,
    user_id: int,
    goal_id: int,
    request: PlanSaveRequest,
) -> list[Task] | None:
    goal = db.scalar(select(Goal).where(Goal.id == goal_id, Goal.user_id == user_id))
    if goal is None:
        return None

    existing = db.scalar(select(AgentRun).where(
        AgentRun.user_id == user_id,
        AgentRun.idempotency_key == str(request.idempotency_key),
    ))
    if existing is not None:
        if existing.goal_id != goal_id or existing.status != "completed":
            raise ValueError("This confirmation key has already been used")
        task_ids = json.loads(existing.output or "[]")
        tasks = list(db.scalars(select(Task).where(Task.id.in_(task_ids), Task.goal_id == goal_id)).all())
        return sorted(tasks, key=lambda task: task.position)

    tasks = [Task(
        goal_id=goal_id,
        title=item.title,
        description=item.description,
        status="pending",
        priority=item.priority,
        estimated_minutes=item.estimated_minutes,
        deadline=item.deadline,
        position=item.position,
    ) for item in request.tasks]
    run = AgentRun(
        user_id=user_id,
        goal_id=goal_id,
        agent_type="rule_planner_save",
        input=str(request.idempotency_key),
        idempotency_key=str(request.idempotency_key),
        output="[]",
        status="completed",
    )
    db.add_all([*tasks, run])
    try:
        db.flush()
        run.output = json.dumps([task.id for task in tasks])
        db.commit()
    except IntegrityError:
        db.rollback()
        # A concurrent retry may have committed the same key first.
        existing = db.scalar(select(AgentRun).where(
            AgentRun.user_id == user_id,
            AgentRun.idempotency_key == str(request.idempotency_key),
        ))
        if existing and existing.goal_id == goal_id and existing.status == "completed":
            task_ids = json.loads(existing.output or "[]")
            return sorted(db.scalars(select(Task).where(Task.id.in_(task_ids), Task.goal_id == goal_id)).all(), key=lambda task: task.position)
        raise
    for task in tasks:
        db.refresh(task)
    return sorted(tasks, key=lambda task: task.position)
