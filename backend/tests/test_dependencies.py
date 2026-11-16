"""API-07 dependencies (FR-04): FS only, cycle detection, planner access. Test plan: TC-08."""
import pytest
from sqlalchemy import func, select

from app.models import AuditLog, Dependency
from app.services.plan import find_cycle_path


@pytest.fixture
def setup(client, make_user, auth_headers):
    """Project PRJ-001 with tasks T-001..T-004, a member planner and an outside planner."""
    make_user("pm.demo", "PROJECT_MANAGER")
    make_user("member.a", "TEAM_MEMBER")
    make_user("planner.in", "PLANNER")
    make_user("planner.out", "PLANNER")
    pm = auth_headers("pm.demo")
    project = client.post("/api/projects", headers=pm, json={
        "project_code": "PRJ-001", "project_name": "بوابة", "planned_start_date": "2026-11-01",
        "planned_end_date": "2026-12-31", "member_usernames": ["member.a", "planner.in"]}).json()
    url = f"/api/projects/{project['project_id']}"
    ids = {}
    for i in range(1, 5):
        task = client.post(f"{url}/tasks", headers=pm, json={
            "task_code": f"T-00{i}", "task_name": f"مهمة {i}", "planned_start_date": "2026-11-01",
            "planned_due_date": "2026-11-05"}).json()
        ids[f"T-00{i}"] = task["task_id"]
    return {"url": f"{url}/dependencies", "ids": ids, "pm": pm, "member": auth_headers("member.a"),
            "planner_in": auth_headers("planner.in"), "planner_out": auth_headers("planner.out"),
            "project_id": project["project_id"]}


def _link(client, setup, pred: str, succ: str, headers=None, **extra):
    return client.post(setup["url"], headers=headers or setup["pm"], json={
        "predecessor_task_id": setup["ids"][pred], "successor_task_id": setup["ids"][succ], **extra})


def test_pm_adds_fs_dependency_with_lag(client, setup, db):
    response = _link(client, setup, "T-001", "T-002", lag_days=2)

    assert response.status_code == 201
    body = response.json()
    assert body["predecessor"]["task_code"] == "T-001" and body["successor"]["task_code"] == "T-002"
    assert body["dependency_type"] == "FS" and body["lag_days"] == 2
    db.expire_all()
    audit = db.scalar(select(AuditLog).where(AuditLog.entity_type == "dependencies"))
    assert audit.action == "create" and audit.new_value["predecessor"] == "T-001"


def test_member_reads_dependencies(client, setup):
    _link(client, setup, "T-001", "T-002")

    listed = client.get(setup["url"], headers=setup["member"])

    assert listed.status_code == 200
    assert [(d["predecessor"]["task_code"], d["successor"]["task_code"]) for d in listed.json()] == \
        [("T-001", "T-002")]


def test_tc08_direct_cycle_between_two_tasks_returns_409_with_path(client, setup, db):
    _link(client, setup, "T-002", "T-004")

    response = _link(client, setup, "T-004", "T-002")

    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "DEPENDENCY_CYCLE"
    assert body["message"].startswith("لا يمكن إضافة العلاقة لأنها تنشئ دورة بين T-004 وT-002")
    assert body["fields"] == [{"field": "cycle_path", "message": "T-004 → T-002 → T-004"}]
    assert db.scalar(select(func.count()).select_from(Dependency)) == 1


def test_indirect_cycle_is_detected_with_full_path(client, setup):
    _link(client, setup, "T-001", "T-002")
    _link(client, setup, "T-002", "T-003")

    response = _link(client, setup, "T-003", "T-001")

    assert response.status_code == 409
    assert response.json()["fields"][0]["message"] == "T-003 → T-001 → T-002 → T-003"


def test_parallel_paths_without_cycle_are_allowed(client, setup):
    for pred, succ in [("T-001", "T-002"), ("T-001", "T-003"), ("T-002", "T-004")]:
        assert _link(client, setup, pred, succ).status_code == 201

    assert _link(client, setup, "T-003", "T-004").status_code == 201  # diamond, not a cycle


def test_duplicate_dependency_returns_409(client, setup):
    _link(client, setup, "T-001", "T-002")

    response = _link(client, setup, "T-001", "T-002")

    assert response.status_code == 409 and response.json()["code"] == "DUPLICATE_DEPENDENCY"


def test_self_dependency_returns_422(client, setup):
    response = _link(client, setup, "T-001", "T-001")

    assert response.status_code == 422
    assert response.json()["fields"][0]["field"] == "successor_task_id"


def test_only_fs_type_is_accepted(client, setup):
    response = _link(client, setup, "T-001", "T-002", dependency_type="SS")

    assert response.status_code == 422
    assert response.json()["fields"][0]["field"] == "dependency_type"


def test_task_of_another_project_returns_422(client, setup):
    other = client.post("/api/projects", headers=setup["pm"], json={
        "project_code": "PRJ-002", "project_name": "آخر", "planned_start_date": "2026-11-01",
        "planned_end_date": "2026-11-30"}).json()
    foreign = client.post(f"/api/projects/{other['project_id']}/tasks", headers=setup["pm"], json={
        "task_code": "X-001", "task_name": "x", "planned_start_date": "2026-11-01",
        "planned_due_date": "2026-11-02"}).json()

    response = client.post(setup["url"], headers=setup["pm"], json={
        "predecessor_task_id": setup["ids"]["T-001"], "successor_task_id": foreign["task_id"]})

    assert response.status_code == 422
    assert response.json()["fields"][0]["field"] == "successor_task_id"


def test_planner_member_can_add_and_delete(client, setup):
    created = _link(client, setup, "T-001", "T-002", headers=setup["planner_in"])
    assert created.status_code == 201

    deleted = client.delete(f"{setup['url']}/{created.json()['dependency_id']}", headers=setup["planner_in"])

    assert deleted.status_code == 204


@pytest.mark.parametrize("who", ["member", "planner_out"])
def test_team_member_and_outside_planner_get_403(client, setup, db, who):
    response = _link(client, setup, "T-001", "T-002", headers=setup[who])

    assert response.status_code == 403
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.action == "access_denied")) == 1


def test_delete_dependency_is_audited_and_unknown_returns_404(client, setup, db):
    dep = _link(client, setup, "T-001", "T-002").json()

    assert client.delete(f"{setup['url']}/{dep['dependency_id']}", headers=setup["pm"]).status_code == 204
    assert client.delete(f"{setup['url']}/{dep['dependency_id']}", headers=setup["pm"]).status_code == 404
    db.expire_all()
    assert db.scalar(select(AuditLog).where(AuditLog.action == "delete")).old_value["successor"] == "T-002"


def test_find_cycle_path_unit():
    edges = [(1, 2), (2, 3), (3, 4), (1, 5)]

    assert find_cycle_path(edges, 4, 1) == [4, 1, 2, 3, 4]
    assert find_cycle_path(edges, 5, 4) is None
    assert find_cycle_path([], 1, 2) is None
