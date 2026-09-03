from datetime import timedelta

from sqlalchemy.orm import Session

from app.agents.planner.service import generate_goal_plan
from app.models.agent_run import AgentRun
from app.models.goal import Goal
from app.models.task import Task


def create_goal_plan(
    db: Session,
    user_id: int,
    user_goal: str,
):
    # AI generation happens before database writes.
    plan = generate_goal_plan(user_goal)

    try:
        goal = Goal(
            user_id=user_id,
            title=plan.title,
            description=plan.description,
            priority=plan.priority,
        )

        db.add(goal)
        db.flush()

        tasks = []

        for planned_task in plan.tasks:
            deadline = None

            if planned_task.deadline_offset_days is not None:
                deadline = goal.created_at + timedelta(
                    days=planned_task.deadline_offset_days
                )

            task = Task(
                goal_id=goal.id,
                title=planned_task.title,
                description=planned_task.description,
                priority=planned_task.priority,
                estimated_minutes=planned_task.estimated_minutes,
                deadline=deadline,
                position=planned_task.position,
            )

            db.add(task)
            tasks.append(task)

        db.flush()

        agent_run = AgentRun(
            user_id=user_id,
            goal_id=goal.id,
            agent_type="planner",
            input=user_goal,
            output=plan.model_dump_json(),
            status="completed",
        )

        db.add(agent_run)

        db.commit()

        db.refresh(goal)

        for task in tasks:
            db.refresh(task)

        db.refresh(agent_run)

        return goal, tasks, agent_run, plan

    except Exception:
        db.rollback()
        raise