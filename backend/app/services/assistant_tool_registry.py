import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.agent_run import AgentRun
from app.models.goal import Goal
from app.models.task import Task
from app.schemas.assistant import (
    AssistantToolRequest,
    AssistantToolResponse,
    CompleteTaskTool,
    CreateGoalTool,
    CreateTaskTool,
    ListGoalsTool,
    ListTasksTool,
)
from app.schemas.goal import GoalResponse
from app.schemas.task import TaskResponse
from app.services.goal_service import get_user_goals
from app.services.task_service import get_user_tasks


_READ_TOOLS = {"list_goals", "list_tasks"}
_WRITE_TOOLS = {"create_goal", "create_task", "complete_task"}


def execute_assistant_tool(
    db: Session,
    user_id: int,
    request: AssistantToolRequest,
) -> AssistantToolResponse:
    """Execute one of the explicitly listed AURA tools for the verified user."""
    if isinstance(request, ListGoalsTool):
        return AssistantToolResponse(
            tool=request.tool,
            goals=[GoalResponse.model_validate(goal) for goal in get_user_goals(db, user_id)],
        )
    if isinstance(request, ListTasksTool):
        return AssistantToolResponse(
            tool=request.tool,
            tasks=[TaskResponse.model_validate(task) for task in get_user_tasks(db, user_id)],
        )
    if request.tool not in _WRITE_TOOLS or request.tool in _READ_TOOLS:
        raise ValueError("Unsupported assistant tool")

    payload = request.model_dump(mode="json", exclude={"idempotency_key"})
    idempotency_key = str(request.idempotency_key)
    existing = db.scalar(select(AgentRun).where(
        AgentRun.user_id == user_id,
        AgentRun.idempotency_key == idempotency_key,
    ))
    if existing is not None:
        if existing.agent_type != "assistant_tool" or existing.input != json.dumps(payload, sort_keys=True):
            raise ValueError("This confirmation key has already been used for a different action")
        if existing.status != "completed" or not existing.output:
            raise ValueError("This action is not in a retryable state")
        saved = json.loads(existing.output)
        result = GoalResponse.model_validate(saved) if request.tool == "create_goal" else TaskResponse.model_validate(saved)
        return AssistantToolResponse(tool=request.tool, result=result, replayed=True)

    run: AgentRun
    result: Goal | Task
    try:
        if isinstance(request, CreateGoalTool):
            result = Goal(user_id=user_id, title=request.title, status="active", priority="medium")
            db.add(result)
            run = AgentRun(
                user_id=user_id,
                agent_type="assistant_tool",
                input=json.dumps(payload, sort_keys=True),
                idempotency_key=idempotency_key,
                status="running",
            )
        elif isinstance(request, CreateTaskTool):
            goal = db.scalar(select(Goal).where(Goal.id == request.goal_id, Goal.user_id == user_id))
            if goal is None:
                raise LookupError("Goal not found")
            result = Task(goal_id=goal.id, title=request.title, status="pending", priority="medium", position=1)
            db.add(result)
            run = AgentRun(
                user_id=user_id,
                goal_id=goal.id,
                agent_type="assistant_tool",
                input=json.dumps(payload, sort_keys=True),
                idempotency_key=idempotency_key,
                status="running",
            )
        elif isinstance(request, CompleteTaskTool):
            result = db.scalar(
                select(Task)
                .join(Goal, Goal.id == Task.goal_id)
                .where(Task.id == request.task_id, Goal.user_id == user_id)
            )
            if result is None:
                raise LookupError("Task not found")
            result.status = "completed"
            run = AgentRun(
                user_id=user_id,
                goal_id=result.goal_id,
                agent_type="assistant_tool",
                input=json.dumps(payload, sort_keys=True),
                idempotency_key=idempotency_key,
                status="running",
            )
        else:
            raise ValueError("Unsupported assistant tool")

        db.add(run)
        db.flush()
        db.refresh(result)
        response: GoalResponse | TaskResponse
        response = GoalResponse.model_validate(result) if isinstance(request, CreateGoalTool) else TaskResponse.model_validate(result)
        run.output = json.dumps(response.model_dump(mode="json"), sort_keys=True)
        run.status = "completed"
        from datetime import datetime, timezone
        run.completed_at = datetime.now(timezone.utc)
        db.commit()
        return AssistantToolResponse(tool=request.tool, result=response)
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(AgentRun).where(
            AgentRun.user_id == user_id,
            AgentRun.idempotency_key == idempotency_key,
        ))
        if existing and existing.agent_type == "assistant_tool" and existing.input == json.dumps(payload, sort_keys=True) and existing.status == "completed" and existing.output:
            saved: dict[str, Any] = json.loads(existing.output)
            response = GoalResponse.model_validate(saved) if request.tool == "create_goal" else TaskResponse.model_validate(saved)
            return AssistantToolResponse(tool=request.tool, result=response, replayed=True)
        raise
    except Exception:
        db.rollback()
        raise
