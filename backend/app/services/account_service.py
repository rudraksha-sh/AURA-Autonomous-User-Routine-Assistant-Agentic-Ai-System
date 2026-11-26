import csv
import io

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.autonomy import AutonomyGrant
from app.models.agent_run import AgentRun
from app.models.goal import Goal
from app.models.integration import Integration
from app.models.notification_preference import UserNotificationPreference
from app.models.otp_code import OtpCode
from app.models.planning import DailySchedule, ScheduleEntry, UserPlanningPreference
from app.models.task import Task
from app.models.external_action import ExternalAction
from app.models.memory import PlanningMemory
from app.models.task_detail import TaskActivity, TaskSubtask
from app.models.user import User
from app.schemas.autonomy import GrantResponse
from app.schemas.daily_planner import PlanningPreferencesResponse
from app.schemas.workflow import WorkflowResponse
from app.models.workflow import WorkflowRun


def export_user_data(db: Session, user_id: int) -> dict:
    goals = list(db.scalars(select(Goal).where(Goal.user_id == user_id).order_by(Goal.id)).all())
    tasks = list(db.scalars(
        select(Task).join(Goal, Goal.id == Task.goal_id).where(Goal.user_id == user_id).order_by(Goal.id, Task.position, Task.id)
    ).all())
    preferences = db.get(UserPlanningPreference, user_id)
    workflows = db.scalars(select(WorkflowRun).where(WorkflowRun.user_id == user_id))
    grants = db.scalars(select(AutonomyGrant).where(AutonomyGrant.user_id == user_id))
    return {
        "planning_preferences": (
            PlanningPreferencesResponse.model_validate(preferences).model_dump(mode="json") if preferences else None
        ),
        "workflows": [WorkflowResponse.model_validate(row).model_dump(mode="json") for row in workflows],
        "autonomy_grants": [GrantResponse.model_validate(row).model_dump(mode="json") for row in grants],
        "goals": [{
            "id": goal.id, "title": goal.title, "description": goal.description, "status": goal.status,
            "priority": goal.priority, "deadline": goal.deadline.isoformat() if goal.deadline else None,
            "created_at": goal.created_at.isoformat() if goal.created_at else None,
            "updated_at": goal.updated_at.isoformat() if goal.updated_at else None,
        } for goal in goals],
        "tasks": [{
            "id": task.id, "goal_id": task.goal_id, "title": task.title, "description": task.description,
            "notes": task.notes, "status": task.status, "priority": task.priority,
            "estimated_minutes": task.estimated_minutes, "deadline": task.deadline.isoformat() if task.deadline else None,
            "position": task.position, "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        } for task in tasks],
    }


def export_user_data_csv(data: dict) -> str:
    output = io.StringIO(newline="")
    columns = ("record_type", "id", "goal_id", "title", "description", "notes", "status", "priority", "deadline", "estimated_minutes", "position", "created_at", "updated_at")
    writer = csv.DictWriter(output, fieldnames=columns)
    writer.writeheader()
    for goal in data["goals"]:
        writer.writerow({"record_type": "goal", **goal})
    for task in data["tasks"]:
        writer.writerow({"record_type": "task", **task})
    return output.getvalue()


def delete_user_account(db: Session, user_id: int) -> str | None:
    user = db.get(User, user_id)
    if user is None:
        return None
    photo_filename = user.profile_photo_filename
    owned_task_ids = list(db.scalars(select(Task.id).join(Goal, Goal.id == Task.goal_id).where(Goal.user_id == user_id)).all())
    owned_schedule_ids = list(db.scalars(select(DailySchedule.id).where(DailySchedule.user_id == user_id)).all())

    db.execute(delete(ScheduleEntry).where(ScheduleEntry.schedule_id.in_(owned_schedule_ids)))
    db.execute(delete(TaskActivity).where(TaskActivity.task_id.in_(owned_task_ids)))
    db.execute(delete(TaskSubtask).where(TaskSubtask.task_id.in_(owned_task_ids)))
    db.execute(delete(DailySchedule).where(DailySchedule.user_id == user_id))
    db.execute(delete(AutonomyGrant).where(AutonomyGrant.user_id == user_id))
    db.execute(delete(WorkflowRun).where(WorkflowRun.user_id == user_id))
    db.execute(delete(AgentRun).where(AgentRun.user_id == user_id))
    db.execute(delete(Task).where(Task.id.in_(owned_task_ids)))
    db.execute(delete(Goal).where(Goal.user_id == user_id))
    db.execute(delete(Integration).where(Integration.user_id == user_id))
    db.execute(delete(UserPlanningPreference).where(UserPlanningPreference.user_id == user_id))
    db.execute(delete(UserNotificationPreference).where(UserNotificationPreference.user_id == user_id))
    db.execute(delete(OtpCode).where(OtpCode.user_id == user_id))
    db.execute(delete(PlanningMemory).where(PlanningMemory.user_id == user_id))
    db.execute(delete(ExternalAction).where(ExternalAction.user_id == user_id))
    db.delete(user)
    db.commit()
    return photo_filename
