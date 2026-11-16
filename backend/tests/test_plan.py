"""API-03 projects, API-04 tasks, API-05 baselines (FR-02, NFR-01, NFR-02, NFR-04).
Test plan: TC-02, TC-04, TC-05, TC-24."""
import pytest
from sqlalchemy import select, text

from app.models import AuditLog, BaselineTask, Task


@pytest.fixture
def team(make_user):
    return {
        "pm": make_user("pm.demo", "PROJECT_MANAGER"),
        "pm2": make_user("pm.other", "PROJECT_MANAGER"),
        "member": make_user("member.a", "TEAM_MEMBER"),
        "outsider": make_user("member.z", "TEAM_MEMBER"),
    }


@pytest.fixture
def pm_headers(team, auth_headers):
    return auth_headers("pm.demo")


@pytest.fixture
def project(client, team, pm_headers) -> dict:
    response = client.post("/api/projects", headers=pm_headers, json={
        "project_code": "PRJ-001", "project_name": "تطوير بوابة خدمات", "planned_start_date": "2026-11-01",
        "planned_end_date": "2027-01-30", "member_usernames": ["member.a"]})
    assert response.status_code == 201, response.text
    return response.json()


def _task(code="T-001", start="2026-11-01", due="2026-11-07", **extra) -> dict:
    return {"task_code": code, "task_name": "تحليل المتطلبات", "planned_start_date": start,
            "planned_due_date": due, **extra}


def _audit(db, action: str, entity_type: str | None = None) -> list[AuditLog]:
    db.expire_all()
    query = select(AuditLog).where(AuditLog.action == action).order_by(AuditLog.audit_id)
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
    return list(db.scalars(query))


# --- API-03 ------------------------------------------------------------------

def test_pm_creates_synthetic_project_with_members(project, team, db):
    assert project["data_mode"] == "synthetic"
    assert project["status"] == "planned"
    assert project["manager"]["username"] == "pm.demo"
    assert {m["username"] for m in project["members"]} == {"pm.demo", "member.a"}
    assert project["task_count"] == 0 and project["current_baseline"] is None and project["can_edit"] is True
    assert len(_audit(db, "create", "projects")) == 1


def test_team_member_cannot_create_project(client, team, auth_headers, db):
    response = client.post("/api/projects", headers=auth_headers("member.a"), json={
        "project_code": "PRJ-009", "project_name": "x", "planned_start_date": "2026-11-01",
        "planned_end_date": "2026-11-30"})

    assert response.status_code == 403
    assert len(_audit(db, "access_denied")) == 1


def test_project_end_before_start_returns_422(client, pm_headers):
    response = client.post("/api/projects", headers=pm_headers, json={
        "project_code": "PRJ-002", "project_name": "x", "planned_start_date": "2026-12-01",
        "planned_end_date": "2026-11-01"})

    assert response.status_code == 422
    assert response.json()["fields"] == [{"field": "planned_end_date",
                                          "message": "تاريخ الانتهاء المخطط يجب ألا يسبق تاريخ البدء المخطط"}]


def test_duplicate_project_code_returns_409(client, project, pm_headers):
    response = client.post("/api/projects", headers=pm_headers, json={
        "project_code": "PRJ-001", "project_name": "x", "planned_start_date": "2026-11-01",
        "planned_end_date": "2026-11-30"})

    assert response.status_code == 409


def test_tc24_switch_to_real_data_without_consent_is_rejected(client, project, pm_headers, db):
    url = f"/api/projects/{project['project_id']}"

    rejected = client.patch(url, headers=pm_headers, json={"data_mode": "real"})

    assert rejected.status_code == 422
    assert {f["field"] for f in rejected.json()["fields"]} == {"consent_ref", "consent_date"}
    assert client.get(url, headers=pm_headers).json()["data_mode"] == "synthetic"

    accepted = client.patch(url, headers=pm_headers, json={
        "data_mode": "real", "consent_ref": "CONSENT-2026-01", "consent_date": "2026-10-20"})

    assert accepted.status_code == 200 and accepted.json()["data_mode"] == "real"
    updates = _audit(db, "update", "projects")
    assert updates[-1].new_value["data_mode"] == "real"


def test_project_list_shows_only_projects_of_the_user(client, project, team, auth_headers):
    assert [p["project_code"] for p in client.get("/api/projects", headers=auth_headers("member.a")).json()] \
        == ["PRJ-001"]
    assert client.get("/api/projects", headers=auth_headers("member.z")).json() == []


def test_member_reads_project_but_outsider_gets_403(client, project, auth_headers, db):
    url = f"/api/projects/{project['project_id']}"

    member_view = client.get(url, headers=auth_headers("member.a"))
    outsider_view = client.get(url, headers=auth_headers("member.z"))

    assert member_view.status_code == 200 and member_view.json()["can_edit"] is False
    assert outsider_view.status_code == 403
    assert len(_audit(db, "access_denied")) == 1


def test_other_manager_cannot_patch_project(client, project, auth_headers):
    response = client.patch(f"/api/projects/{project['project_id']}", headers=auth_headers("pm.other"),
                            json={"project_name": "تغيير"})

    assert response.status_code == 403


def test_pm_updates_members_by_username(client, project, pm_headers):
    response = client.patch(f"/api/projects/{project['project_id']}", headers=pm_headers,
                            json={"member_usernames": [" Member.Z "]})

    assert response.status_code == 200
    assert {m["username"] for m in response.json()["members"]} == {"pm.demo", "member.z"}


def test_unknown_member_username_returns_422(client, project, pm_headers):
    response = client.patch(f"/api/projects/{project['project_id']}", headers=pm_headers,
                            json={"member_usernames": ["member.a", "ghost.user"]})

    assert response.status_code == 422
    field = response.json()["fields"][0]
    assert field["field"] == "member_usernames" and "ghost.user" in field["message"]


def test_unknown_project_returns_404(client, pm_headers):
    assert client.get("/api/projects/9999", headers=pm_headers).status_code == 404


# --- API-04 ------------------------------------------------------------------

def test_pm_creates_task_and_member_can_read_it(client, project, team, pm_headers, auth_headers):
    url = f"/api/projects/{project['project_id']}/tasks"

    created = client.post(url, headers=pm_headers,
                          json=_task(priority="high", assignee_user_id=team["member"].user_id))

    assert created.status_code == 201
    body = created.json()
    assert body["planned_duration_days"] == 7
    assert body["assignee"]["username"] == "member.a" and body["has_snapshots"] is False
    listed = client.get(url, headers=auth_headers("member.a"))
    assert [t["task_code"] for t in listed.json()] == ["T-001"]


def test_tc05_due_date_before_start_returns_422_under_the_field(client, project, pm_headers, db):
    response = client.post(f"/api/projects/{project['project_id']}/tasks", headers=pm_headers,
                           json=_task(start="2026-11-10", due="2026-11-05"))

    assert response.status_code == 422
    assert response.json()["fields"] == [{"field": "planned_due_date",
                                          "message": "تاريخ الاستحقاق يجب ألا يسبق تاريخ البدء"}]
    assert db.scalar(select(Task.task_id)) is None


def test_invalid_priority_and_date_format_return_422(client, project, pm_headers):
    response = client.post(f"/api/projects/{project['project_id']}/tasks", headers=pm_headers,
                           json=_task(due="07-11-2026", priority="urgent"))

    assert response.status_code == 422
    assert {f["field"] for f in response.json()["fields"]} == {"planned_due_date", "priority"}


def test_assignee_must_be_project_member(client, project, team, pm_headers):
    response = client.post(f"/api/projects/{project['project_id']}/tasks", headers=pm_headers,
                           json=_task(assignee_user_id=team["outsider"].user_id))

    assert response.status_code == 422
    assert response.json()["fields"][0]["field"] == "assignee_user_id"


def test_duplicate_task_code_returns_409(client, project, pm_headers):
    url = f"/api/projects/{project['project_id']}/tasks"
    client.post(url, headers=pm_headers, json=_task())

    assert client.post(url, headers=pm_headers, json=_task()).status_code == 409


def test_tc02_team_member_patch_returns_403_without_change(client, project, team, pm_headers, auth_headers, db):
    task = client.post(f"/api/projects/{project['project_id']}/tasks", headers=pm_headers,
                       json=_task(assignee_user_id=team["member"].user_id)).json()

    response = client.patch(f"/api/projects/{project['project_id']}/tasks/{task['task_id']}",
                            headers=auth_headers("member.a"), json={"planned_due_date": "2026-11-20"})

    assert response.status_code == 403
    assert response.json()["message"] == "ليست لديك صلاحية لتعديل خطة هذا المشروع"
    db.expire_all()
    assert str(db.get(Task, task["task_id"]).planned_due_date) == "2026-11-07"
    denied = _audit(db, "access_denied")
    assert len(denied) == 1 and denied[0].user_id == team["member"].user_id


def test_pm_patches_task_and_update_is_audited(client, project, pm_headers, db):
    task = client.post(f"/api/projects/{project['project_id']}/tasks", headers=pm_headers, json=_task()).json()

    response = client.patch(f"/api/projects/{project['project_id']}/tasks/{task['task_id']}",
                            headers=pm_headers, json={"planned_due_date": "2026-11-10"})

    assert response.status_code == 200 and response.json()["planned_duration_days"] == 10
    update = _audit(db, "update", "tasks")[-1]
    assert update.old_value == {"planned_due_date": "2026-11-07"}
    assert update.new_value == {"planned_due_date": "2026-11-10"}


def test_patch_that_makes_due_before_start_returns_422(client, project, pm_headers):
    task = client.post(f"/api/projects/{project['project_id']}/tasks", headers=pm_headers, json=_task()).json()

    response = client.patch(f"/api/projects/{project['project_id']}/tasks/{task['task_id']}",
                            headers=pm_headers, json={"planned_start_date": "2026-11-20"})

    assert response.status_code == 422


def test_task_of_another_project_returns_404(client, project, pm_headers):
    other = client.post("/api/projects", headers=pm_headers, json={
        "project_code": "PRJ-002", "project_name": "آخر", "planned_start_date": "2026-11-01",
        "planned_end_date": "2026-11-30"}).json()
    task = client.post(f"/api/projects/{other['project_id']}/tasks", headers=pm_headers, json=_task()).json()

    response = client.patch(f"/api/projects/{project['project_id']}/tasks/{task['task_id']}",
                            headers=pm_headers, json={"task_name": "x"})

    assert response.status_code == 404


def test_pm_deletes_task_without_snapshots(client, project, pm_headers, db):
    task = client.post(f"/api/projects/{project['project_id']}/tasks", headers=pm_headers, json=_task()).json()

    response = client.delete(f"/api/projects/{project['project_id']}/tasks/{task['task_id']}", headers=pm_headers)

    assert response.status_code == 204
    assert len(_audit(db, "delete", "tasks")) == 1


def test_delete_task_with_snapshots_returns_409(client, project, team, pm_headers, db):
    url = f"/api/projects/{project['project_id']}"
    task = client.post(f"{url}/tasks", headers=pm_headers, json=_task()).json()
    baseline = client.post(f"{url}/baselines", headers=pm_headers, json={}).json()
    db.execute(text("""INSERT INTO task_snapshots (task_id, baseline_id, snapshot_date, update_source,
                       progress_pct, status_at_snapshot, recorded_by)
                       VALUES (:t, :b, current_date, 'manual', 10, 'in_progress', :u)"""),
               {"t": task["task_id"], "b": baseline["baseline_id"], "u": team["pm"].user_id})
    db.commit()

    response = client.delete(f"{url}/tasks/{task['task_id']}", headers=pm_headers)

    assert response.status_code == 409 and response.json()["code"] == "TASK_HAS_SNAPSHOTS"
    listed = client.get(f"{url}/tasks", headers=pm_headers).json()
    assert listed[0]["has_snapshots"] is True


# --- API-05 ------------------------------------------------------------------

def test_tc04_three_tasks_then_baseline_version_1(client, project, pm_headers, db):
    url = f"/api/projects/{project['project_id']}"
    for i, (start, due) in enumerate([("2026-11-01", "2026-11-07"), ("2026-11-08", "2026-11-14"),
                                      ("2026-11-15", "2026-11-28")], start=1):
        client.post(f"{url}/tasks", headers=pm_headers, json=_task(code=f"T-00{i}", start=start, due=due))

    response = client.post(f"{url}/baselines", headers=pm_headers, json={"note": "الخطة الأولى"})

    assert response.status_code == 201
    body = response.json()
    assert body["version_no"] == 1 and body["task_count"] == 3
    rows = list(db.scalars(select(BaselineTask).where(BaselineTask.baseline_id == body["baseline_id"])))
    assert len(rows) == 3
    detail = client.get(url, headers=pm_headers).json()
    assert detail["current_baseline"]["version_no"] == 1 and detail["task_count"] == 3


def test_second_baseline_gets_version_2_and_keeps_version_1(client, project, pm_headers, db):
    url = f"/api/projects/{project['project_id']}"
    task = client.post(f"{url}/tasks", headers=pm_headers, json=_task()).json()
    first = client.post(f"{url}/baselines", headers=pm_headers, json={}).json()
    client.patch(f"{url}/tasks/{task['task_id']}", headers=pm_headers, json={"planned_due_date": "2026-11-12"})

    second = client.post(f"{url}/baselines", headers=pm_headers).json()

    assert second["version_no"] == 2
    kept = db.scalar(select(BaselineTask).where(BaselineTask.baseline_id == first["baseline_id"]))
    assert str(kept.planned_due_date) == "2026-11-07"


def test_baseline_of_project_without_tasks_returns_409(client, project, pm_headers):
    response = client.post(f"/api/projects/{project['project_id']}/baselines", headers=pm_headers, json={})

    assert response.status_code == 409 and response.json()["code"] == "NO_TASKS"


def test_member_cannot_save_baseline(client, project, pm_headers, auth_headers):
    url = f"/api/projects/{project['project_id']}"
    client.post(f"{url}/tasks", headers=pm_headers, json=_task())

    assert client.post(f"{url}/baselines", headers=auth_headers("member.a"), json={}).status_code == 403
