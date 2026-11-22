from uuid import uuid4

from tests.workflows.test_goal_workflow import headers, start_plan


def test_changed_goal_requires_new_approval_and_replanning_is_tenant_scoped(client):
    auth = headers(client, "replan-owner@example.com")
    other = headers(client, "replan-other@example.com")
    payload, original = start_plan(client, auth)
    _, other_run = start_plan(client, other)

    updated = client.patch(f"/api/goals/{payload['goal_id']}", headers=auth, json={"title": "Read two books"})
    assert updated.status_code == 200, updated.text
    original_path = f"/api/v1/workflows/{original['id']}"
    stale = client.post(original_path + "/transition", headers=auth, json={"operation": "approve", "revision": 0})
    assert stale.status_code == 409
    assert client.get(original_path, headers=auth).json()["revision"] == 0
    assert client.post("/api/v1/workflows", headers=other, json={
        **payload, "run_id": str(uuid4()),
    }).status_code == 404
    assert client.post("/api/v1/workflows", headers=auth, json={
        **payload, "run_id": str(uuid4()), "previous_run_id": other_run["id"],
    }).status_code == 404

    revised = client.post("/api/v1/workflows", headers=auth, json={
        **payload, "run_id": str(uuid4()), "previous_run_id": original["id"], "task_count": 3,
    })
    assert revised.status_code == 201, revised.text
    run = revised.json()
    assert run["status"] == "awaiting_approval"
    assert run["result"]["plan"]["goal_title"] == "Read two books"
    assert run["result"]["comparison"]["previous_task_count"] == 5
    assert run["result"]["comparison"]["proposed_task_count"] == 3
    assert client.post(f"/api/v1/workflows/{run['id']}/transition", headers=auth, json={
        "operation": "approve", "revision": 0,
    }).status_code == 200


def test_preferences_are_explicitly_saved_exported_and_reset(client):
    auth = headers(client, "workflow-memory@example.com")
    response = client.put("/api/planner/preferences", headers=auth, json={"daily_capacity_minutes": 180})
    assert response.status_code == 200, response.text
    exported = client.get("/api/profile/export", headers=auth).json()
    assert exported["planning_preferences"]["daily_capacity_minutes"] == 180
    assert client.delete("/api/planner/preferences", headers=auth).status_code == 204
    assert client.get("/api/planner/preferences", headers=auth).json()["daily_capacity_minutes"] == 360
    assert client.get("/api/profile/export", headers=auth).json()["planning_preferences"] is None
