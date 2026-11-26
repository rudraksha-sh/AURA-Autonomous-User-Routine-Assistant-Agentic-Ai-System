import hashlib
import json
from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agents.replanning.schemas import ConstraintVersion, PlanComparison
from app.models.goal import Goal
from app.models.task import Task
from app.models.workflow import WorkflowRun
from app.services.planner_service import stage_goal_tasks
from app.tools.recovery import snapshot_task

VERSION: ConstraintVersion = "goal-plan-v1"


def goal_version(goal: Goal) -> str:
    values = [VERSION, goal.id, goal.title, goal.description, goal.priority, goal.status,
              goal.deadline.isoformat() if goal.deadline else None]
    return hashlib.sha256(json.dumps(values, ensure_ascii=True).encode()).hexdigest()



def compare_plans(db: Session, user_id: int, goal_id: int, previous_run_id: str, plan: dict) -> PlanComparison:
    previous = db.scalar(select(WorkflowRun).where(
        WorkflowRun.id == previous_run_id, WorkflowRun.user_id == user_id, WorkflowRun.goal_id == goal_id,
    ))
    if previous is None or not previous.result.get("plan"):
        raise LookupError("Previous plan not found")
    before = previous.result["plan"]["tasks"]
    after = plan["tasks"]
    overdue = db.scalar(select(func.count(Task.id)).join(Goal, Goal.id == Task.goal_id).where(
        Goal.user_id == user_id, Goal.id == goal_id, Task.status != "completed",
        Task.deadline < datetime.now(timezone.utc),
    ))
    return PlanComparison(
        previous_run_id=previous_run_id, previous_task_count=len(before), proposed_task_count=len(after),
        estimated_minutes_change=sum(item["estimated_minutes"] for item in after)
        - sum(item["estimated_minutes"] for item in before),
        overdue_task_count=overdue,
    )

def _parent_query(user_id: int, goal_id: int, run_id: str):
    return select(WorkflowRun).where(
        WorkflowRun.id == run_id, WorkflowRun.user_id == user_id, WorkflowRun.goal_id == goal_id,
    )


def _receipt_tasks(db: Session, user_id: int, goal_id: int, ids, *, lock: bool = False):
    query = select(Task).join(Goal).where(
        Goal.user_id == user_id, Task.goal_id == goal_id, Task.id.in_(ids),
    ).order_by(Task.id)
    if lock:
        query = query.with_for_update(of=Task).execution_options(populate_existing=True)
    return {str(task.id): task for task in db.scalars(query)}


def preview_reconciliation(db: Session, user_id: int, goal_id: int, run_id: str, plan: dict):
    parent = db.scalar(_parent_query(user_id, goal_id, run_id))
    if parent is None or not parent.result.get("plan"):
        raise LookupError("Previous plan not found")
    if parent.result.get("_replan_run_id"):
        raise ValueError("This plan has already been replaced. Preview from the latest workflow.")
    evidence = parent.result.get("evidence", {}) if parent.status == "completed" else {}
    prior = evidence.get("_task_snapshots", {})
    ids = evidence.get("task_ids", [])
    tasks = _receipt_tasks(db, user_id, goal_id, ids)
    expected = {key: snapshot_task(task) for key, task in tasks.items()}
    positions = evidence.get("_task_positions") or {
        str(index): str(task_id) for index, task_id in enumerate(sorted(ids), 1)
    }
    updates, preserved, skipped = {}, [], []
    protected = evidence.get("_protected_task_ids", [])
    proposal_positions = {str(task["position"]) for task in plan["tasks"]}
    for position, task_id in positions.items():
        if task_id not in tasks:
            continue
        if (position not in proposal_positions or tasks[task_id].status != "pending"
                or int(task_id) in protected or prior.get(task_id) != expected[task_id]):
            preserved.append(int(task_id))
            skipped.append(int(position))
        else:
            updates[position] = task_id
    return {
        "parent_id": parent.id, "parent_revision": parent.revision, "ids": ids, "expected": expected,
        "positions": positions, "updates": updates, "preserved": preserved, "skipped": skipped,
    }


def lock_replan_parent(db: Session, user_id: int, goal_id: int, reviewed: dict) -> WorkflowRun:
    parent = db.scalar(_parent_query(user_id, goal_id, reviewed["parent_id"])
                       .with_for_update().execution_options(populate_existing=True))
    if parent is None or parent.revision != reviewed["parent_revision"] or parent.result.get("_replan_run_id"):
        raise ValueError("The previous workflow changed. Preview a new revision.")
    return parent


def apply_reconciliation(db: Session, parent: WorkflowRun, run_id: str, reviewed: dict, proposals):
    user_id, goal_id = parent.user_id, parent.goal_id
    tasks = _receipt_tasks(db, user_id, goal_id, reviewed["ids"], lock=True)
    if {key: snapshot_task(task) for key, task in tasks.items()} != reviewed["expected"]:
        raise ValueError("Tasks changed after the preview. Preview a new revision.")

    positions = {position: task_id for position, task_id in reviewed["positions"].items() if task_id in tasks}
    for proposal in proposals:
        position = str(proposal.position)
        if proposal.position in reviewed["skipped"]:
            continue
        if position in reviewed["updates"]:
            task = tasks[reviewed["updates"][position]]
            for field in ("title", "description", "priority", "estimated_minutes", "deadline"):
                setattr(task, field, getattr(proposal, field))
        else:
            task, = stage_goal_tasks(db, goal_id, [proposal])
            db.flush()
            tasks[str(task.id)] = task
            positions[position] = str(task.id)
    parent.revision += 1
    parent.result = {**parent.result, "_replan_run_id": run_id}
    if parent.status in ("awaiting_approval", "paused"):
        parent.status, parent.checkpoint = "cancelled", []
        parent.result = {
            **parent.result, "approval_status": "cancelled",
            "trace": [*parent.result["trace"], {"agent": "replanning", "outcome": "superseded",
                                               "at": datetime.now(timezone.utc).isoformat()}],
        }
    db.flush()
    return {key: snapshot_task(task) for key, task in tasks.items()}, positions

def detect_replan_signals(db: Session, row: WorkflowRun):
    """Check a bounded receipt and one saved day without changing tasks or workflows."""
    from app.services.daily_planner_service import _utc_timestamp, read_daily_schedule

    evidence = row.result.get("evidence", {})
    ids = evidence.get("task_ids", [])[:8]
    expected = evidence.get("_task_snapshots", {})
    tasks = _receipt_tasks(db, row.user_id, row.goal_id, ids)
    changed = sorted(task.id for key, task in tasks.items() if key in expected and snapshot_task(task) != expected[key])
    missing = sorted(set(ids) - {task.id for task in tasks.values()})
    overdue = sorted(task.id for task in tasks.values()
                     if task.status != "completed" and task.deadline and _utc_timestamp(task.deadline) < datetime.now(timezone.utc).timestamp())
    preview = row.result.get("schedule") or {}
    conflicts = set()
    if preview.get("target_date"):
        saved = read_daily_schedule(db, row.user_id, date.fromisoformat(preview["target_date"]))
        positions = evidence.get("_task_positions") or {
            str(index): str(task_id) for index, task_id in enumerate(sorted(ids), 1)
        }
        if saved:
            for entry in preview.get("entries", [])[:40]:
                task_id = entry["task_id"]
                if task_id < 0:
                    task_id = int(positions.get(str(-task_id), 0))
                if task_id not in ids or str(task_id) not in tasks or tasks[str(task_id)].status == "completed":
                    continue
                start, end = (_utc_timestamp(datetime.fromisoformat(entry[key])) for key in ("start_at", "end_at"))
                if any(item.task_id != task_id and _utc_timestamp(item.start_at) < end
                       and _utc_timestamp(item.end_at) > start for item in saved.entries):
                    conflicts.add(task_id)
    return {
        "changed_task_ids": changed, "missing_task_ids": missing, "overdue_task_ids": overdue,
        "conflicting_task_ids": sorted(conflicts),
        "needs_review": bool(changed or missing or overdue or conflicts),
    }
