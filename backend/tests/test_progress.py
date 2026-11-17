"""API-06 task snapshots and "my tasks" (FR-03, NFR-04, ARC-03, SEC-08). Test plan: TC-06, TC-07."""
from datetime import date, timedelta

import pytest
from sqlalchemy import func, select

from app.models import AuditLog, TaskSnapshot


@pytest.fixture
def setup(client, make_user, auth_headers, add_members):
    """PM with one project, two members, one task assigned to member.a, and baseline v1."""
    make_user("pm.demo", "PROJECT_MANAGER")
    member_a_id = make_user("member.a", "TEAM_MEMBER").user_id
    make_user("member.b", "TEAM_MEMBER")
    make_user("member.z", "TEAM_MEMBER")
    pm = auth_headers("pm.demo")
    project = client.post("/api/projects", headers=pm, json={
        "project_code": "PRJ-001", "project_name": "بوابة", "planned_start_date": "2026-11-01",
        "planned_end_date": "2026-12-31"}).json()
    add_members(pm, project["project_id"], ["member.a", "member.b"])
    task = client.post(f"/api/projects/{project['project_id']}/tasks", headers=pm, json={
        "task_code": "T-001", "task_name": "تحليل", "planned_start_date": "2026-11-01",
        "planned_due_date": "2026-11-10", "assignee_user_id": member_a_id}).json()
    client.post(f"/api/projects/{project['project_id']}/baselines", headers=pm, json={})
    return {"project": project, "task": task, "pm": pm, "a": auth_headers("member.a"),
            "b": auth_headers("member.b"), "z": auth_headers("member.z")}


def _url(setup) -> str:
    return f"/api/tasks/{setup['task']['task_id']}/snapshots"


def _snap(day: str, pct: float, status: str = "in_progress", **extra) -> dict:
    return {"snapshot_date": day, "progress_pct": pct, "status_at_snapshot": status, **extra}


def test_assignee_records_snapshot_linked_to_current_baseline(client, setup, db):
    response = client.post(_url(setup), headers=setup["a"],
                           json=_snap("2026-11-03", 30, remaining_estimate_days=5, blocker_note=None))

    assert response.status_code == 201
    body = response.json()
    assert body["progress_pct"] == 30.0 and body["status_at_snapshot"] == "in_progress"
    assert body["baseline_version"] == 1 and body["update_source"] == "manual"
    assert body["recorded_by"]["username"] == "member.a"
    db.expire_all()
    audit = db.scalar(select(AuditLog).where(AuditLog.entity_type == "task_snapshots"))
    assert audit.action == "create" and audit.new_value["progress_pct"] == 30.0


def test_tc06_two_snapshots_are_both_kept_and_latest_is_shown(client, setup, db):
    first = client.post(_url(setup), headers=setup["a"], json=_snap("2026-11-03", 30))
    second = client.post(_url(setup), headers=setup["a"], json=_snap("2026-11-06", 60))

    assert first.status_code == second.status_code == 201
    history = client.get(_url(setup), headers=setup["pm"]).json()
    assert [s["progress_pct"] for s in history] == [60.0, 30.0]
    assert db.scalar(select(func.count()).select_from(TaskSnapshot)) == 2
    mine = client.get("/api/tasks?assignee=me", headers=setup["a"]).json()
    assert mine[0]["latest_snapshot"]["progress_pct"] == 60.0
    assert mine[0]["latest_snapshot"]["snapshot_date"] == "2026-11-06"


@pytest.mark.parametrize("payload, field, message", [
    (_snap("2026-11-03", 120), "progress_pct", "نسبة الإنجاز يجب أن تكون بين 0 و100"),
    (_snap("2026-11-03", -5), "progress_pct", "نسبة الإنجاز يجب أن تكون بين 0 و100"),
    (_snap("2026-11-03", 80, "completed"), "progress_pct", "الحالة «مكتملة» تتطلب نسبة إنجاز 100"),
])
def test_tc07_invalid_progress_is_rejected_with_422(client, setup, db, payload, field, message):
    response = client.post(_url(setup), headers=setup["a"], json=payload)

    assert response.status_code == 422
    assert response.json()["fields"] == [{"field": field, "message": message}]
    assert db.scalar(select(func.count()).select_from(TaskSnapshot)) == 0


def test_completed_with_100_is_accepted(client, setup):
    response = client.post(_url(setup), headers=setup["a"], json=_snap("2026-11-09", 100, "completed"))

    assert response.status_code == 201


def test_future_snapshot_date_is_rejected(client, setup):
    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    response = client.post(_url(setup), headers=setup["a"], json=_snap(tomorrow, 10))

    assert response.status_code == 422
    assert response.json()["fields"][0]["field"] == "snapshot_date"


def test_unknown_status_and_negative_remaining_are_rejected(client, setup):
    response = client.post(_url(setup), headers=setup["a"],
                           json=_snap("2026-11-03", 10, "done", remaining_estimate_days=-1))

    assert response.status_code == 422
    assert "status_at_snapshot" in {f["field"] for f in response.json()["fields"]}


def test_project_manager_can_record_snapshot(client, setup):
    assert client.post(_url(setup), headers=setup["pm"], json=_snap("2026-11-03", 20)).status_code == 201


def test_other_member_cannot_record_snapshot_and_denial_is_audited(client, setup, db):
    response = client.post(_url(setup), headers=setup["b"], json=_snap("2026-11-03", 20))

    assert response.status_code == 403
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.action == "access_denied")) == 1
    assert db.scalar(select(func.count()).select_from(TaskSnapshot)) == 0


def test_assignee_cannot_cancel_task_and_denial_is_audited(client, setup, db):
    response = client.post(_url(setup), headers=setup["a"], json=_snap("2026-11-03", 30, "cancelled"))

    assert response.status_code == 403
    assert response.json()["message"] == "إلغاء المهمة (الحالة «ملغاة») يسجله مدير المشروع فقط"
    db.expire_all()
    denied = list(db.scalars(select(AuditLog).where(AuditLog.action == "access_denied")))
    assert len(denied) == 1 and denied[0].entity_type == "tasks"
    assert db.scalar(select(func.count()).select_from(TaskSnapshot)) == 0


def test_project_manager_can_cancel_task(client, setup):
    response = client.post(_url(setup), headers=setup["pm"], json=_snap("2026-11-03", 30, "cancelled"))

    assert response.status_code == 201
    assert response.json()["status_at_snapshot"] == "cancelled"


def test_member_reads_history_but_outsider_gets_403(client, setup):
    client.post(_url(setup), headers=setup["a"], json=_snap("2026-11-03", 20))

    assert client.get(_url(setup), headers=setup["b"]).status_code == 200
    assert client.get(_url(setup), headers=setup["z"]).status_code == 403


def test_snapshot_without_baseline_returns_409(client, setup):
    pm = setup["pm"]
    project_id = setup["project"]["project_id"]
    task = client.post(f"/api/projects/{project_id}/tasks", headers=pm, json={
        "task_code": "T-002", "task_name": "جديدة", "planned_start_date": "2026-11-01",
        "planned_due_date": "2026-11-05"}).json()
    other = client.post("/api/projects", headers=pm, json={
        "project_code": "PRJ-002", "project_name": "بلا خط أساس", "planned_start_date": "2026-11-01",
        "planned_end_date": "2026-11-30"}).json()
    lonely = client.post(f"/api/projects/{other['project_id']}/tasks", headers=pm, json={
        "task_code": "T-001", "task_name": "x", "planned_start_date": "2026-11-01",
        "planned_due_date": "2026-11-05"}).json()

    assert client.post(f"/api/tasks/{task['task_id']}/snapshots", headers=pm,
                       json=_snap("2026-11-03", 5)).status_code == 201  # project has baseline v1
    response = client.post(f"/api/tasks/{lonely['task_id']}/snapshots", headers=pm, json=_snap("2026-11-03", 5))
    assert response.status_code == 409 and response.json()["code"] == "NO_BASELINE"


def test_snapshot_uses_latest_baseline_version(client, setup):
    client.post(f"/api/projects/{setup['project']['project_id']}/baselines", headers=setup["pm"], json={})

    response = client.post(_url(setup), headers=setup["a"], json=_snap("2026-11-03", 20))

    assert response.json()["baseline_version"] == 2


@pytest.mark.parametrize("method", ["put", "patch", "delete"])
def test_snapshots_cannot_be_changed_or_deleted(client, setup, method):
    created = client.post(_url(setup), headers=setup["a"], json=_snap("2026-11-03", 20)).json()

    response = getattr(client, method)(f"{_url(setup)}/{created['snapshot_id']}", headers=setup["a"])

    assert response.status_code in (404, 405)


def test_unknown_task_returns_404(client, setup):
    assert client.get("/api/tasks/9999/snapshots", headers=setup["pm"]).status_code == 404


def test_my_tasks_lists_only_tasks_assigned_to_me(client, setup):
    mine = client.get("/api/tasks?assignee=me", headers=setup["a"])
    others = client.get("/api/tasks?assignee=me", headers=setup["b"])

    assert mine.status_code == 200
    assert [(t["task_code"], t["project"]["project_code"]) for t in mine.json()] == [("T-001", "PRJ-001")]
    assert mine.json()[0]["latest_snapshot"] is None
    assert others.json() == []


def test_my_tasks_requires_assignee_me(client, setup):
    assert client.get("/api/tasks", headers=setup["a"]).status_code == 422
    assert client.get("/api/tasks?assignee=member.b", headers=setup["a"]).status_code == 422
