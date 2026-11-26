from base64 import b64decode, b64encode

import pytest

from app.agents.replanning.agent import goal_version
from app.agents.context.agent import load_goal
from app.db.session import SessionLocal
from app.models.workflow import WorkflowRun
from app.schemas.planner import PlanRequest
from app.services.planner_service import generate_goal_plan
from app.workflows import nodes
from app.workflows.checkpoints import TransactionJournal
from tests.workflows.test_goal_workflow import headers, start_plan
from tests.workflows.test_reliability import assert_pending, transition


@pytest.mark.parametrize("legacy", [True, False], ids=["legacy", "versioned"])
def test_compatible_context_checkpoint_resumes(client, monkeypatch, legacy):
    auth = headers(client, "checkpoint-format@example.com")

    def legacy_context(state, db):
        context = load_goal(db, state["user_id"], state["goal_id"])
        return {"goal_version": goal_version(context.goal), "evidence": {"source": context.source},
                **nodes.event(state, "context")}

    def legacy_plan(state, db):
        goal = load_goal(db, state["user_id"], state["goal_id"]).goal
        plan = generate_goal_plan(goal, PlanRequest(task_count=state["task_count"]).task_count)
        return {"plan": plan.model_dump(mode="json"), "proposed_actions": state["permitted_scopes"],
                **nodes.event(state, "planner")}

    with monkeypatch.context() as patch:
        if legacy:
            patch.setattr(nodes, "collect_context", legacy_context)
            patch.setattr(nodes, "plan", legacy_plan)
        _, run = start_plan(client, auth)

    assert (run["result"]["evidence"]["context"] is None) == legacy
    result = transition(client, auth, run, "approve")
    assert result.status_code == 200, result.text
    assert len(result.json()["result"]["evidence"]["task_ids"]) == 5


@pytest.mark.parametrize("incompatibility", ["future-version", "missing-evidence", "missing-snapshot"])
def test_incompatible_context_checkpoint_preserves_pending_run(client, incompatibility):
    auth = headers(client, "checkpoint-incompatible@example.com")
    _, run = start_plan(client, auth)
    serializer = TransactionJournal().serde

    def change(value):
        if isinstance(value, dict):
            if incompatibility == "future-version" and "schema_version" in value:
                value["schema_version"] = 99
            if incompatibility == "missing-evidence" and value.get("source") == "aura.goal":
                value.pop("context", None)
            if incompatibility == "missing-snapshot":
                value.pop("context_snapshot", None)
            for item in value.values():
                change(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                change(item)

    with SessionLocal() as db:
        row = db.get(WorkflowRun, run["id"])
        journal = []
        for method, kind, encoded in row.checkpoint:
            args = serializer.loads_typed((kind, b64decode(encoded)))
            change(args)
            kind, payload = serializer.dumps_typed(args)
            journal.append([method, kind, b64encode(payload).decode("ascii")])
        row.checkpoint = journal
        db.commit()
    result = transition(client, auth, run, "approve")
    assert result.status_code == 409, result.text
    assert_pending(run, journal)
    assert transition(client, auth, run, "cancel").status_code == 200
