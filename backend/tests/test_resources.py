"""API-08 resources, availability and allocation (FR-05, NFR-01). Test plan: TC-09."""
from datetime import date

import pytest
from sqlalchemy import func, select

from app.models import AuditLog
from app.services.resources import latest_availability


@pytest.fixture
def setup(client, make_user, auth_headers):
    make_user("pm.demo", "PROJECT_MANAGER")
    make_user("pm.other", "PROJECT_MANAGER")
    make_user("member.a", "TEAM_MEMBER")
    make_user("planner.in", "PLANNER")
    make_user("planner.out", "PLANNER")
    pm = auth_headers("pm.demo")
    project = client.post("/api/projects", headers=pm, json={
        "project_code": "PRJ-001", "project_name": "بوابة", "planned_start_date": "2026-11-01",
        "planned_end_date": "2026-12-31", "member_usernames": ["member.a", "planner.in"]}).json()
    task = client.post(f"/api/projects/{project['project_id']}/tasks", headers=pm, json={
        "task_code": "T-001", "task_name": "تطوير", "planned_start_date": "2026-11-01",
        "planned_due_date": "2026-11-10"}).json()
    return {"pm": pm, "task": task, "member": auth_headers("member.a"), "pm_other": auth_headers("pm.other"),
            "planner_in": auth_headers("planner.in"), "planner_out": auth_headers("planner.out")}


def _resource(client, headers, code="R1", **extra):
    body = {"resource_code": code, "resource_type": "human", "default_capacity_hours": 8, **extra}
    return client.post("/api/resources", headers=headers, json=body)


# --- resources ---------------------------------------------------------------

def test_pm_creates_human_resource_linked_by_username(client, setup, db):
    response = _resource(client, setup["pm"], linked_username="member.a")

    assert response.status_code == 201
    body = response.json()
    assert body["resource_code"] == "R1" and body["linked_user"]["username"] == "member.a"
    assert body["default_capacity_hours"] == 8.0 and body["latest_availability"] is None
    db.expire_all()
    assert db.scalar(select(AuditLog).where(AuditLog.entity_type == "resources")).action == "create"


def test_planner_creates_equipment_resource(client, setup):
    response = _resource(client, setup["planner_out"], code="EQ-1", resource_type="equipment")

    assert response.status_code == 201 and response.json()["linked_user"] is None


def test_team_member_cannot_manage_resources(client, setup):
    assert client.get("/api/resources", headers=setup["member"]).status_code == 403
    assert _resource(client, setup["member"]).status_code == 403


@pytest.mark.parametrize("capacity", [0, 25, -1])
def test_capacity_must_be_between_0_and_24(client, setup, capacity):
    response = _resource(client, setup["pm"], default_capacity_hours=capacity)

    assert response.status_code == 422
    assert response.json()["fields"] == [{"field": "default_capacity_hours",
                                          "message": "السعة اليومية يجب أن تكون أكبر من 0 ولا تزيد على 24 ساعة"}]


def test_duplicate_code_and_double_linked_user_return_409(client, setup):
    _resource(client, setup["pm"], linked_username="member.a")

    assert _resource(client, setup["pm"]).status_code == 409
    assert _resource(client, setup["pm"], code="R2", linked_username="member.a").status_code == 409


def test_unknown_linked_username_and_type_return_422(client, setup):
    response = _resource(client, setup["pm"], linked_username="ghost", resource_type="robot")

    assert response.status_code == 422


def test_patch_resource_deactivates_and_is_audited(client, setup, db):
    resource = _resource(client, setup["pm"]).json()

    response = client.patch(f"/api/resources/{resource['resource_id']}", headers=setup["pm"],
                            json={"is_active": False, "default_capacity_hours": 6})

    assert response.status_code == 200 and response.json()["is_active"] is False
    db.expire_all()
    update = db.scalar(select(AuditLog).where(AuditLog.action == "update"))
    assert update.old_value == {"is_active": True, "default_capacity_hours": 8.0}


# --- availability (TC-09) ----------------------------------------------------

def test_tc09_availability_60_on_a_date_is_saved_and_read_as_of_that_date(client, setup, db):
    resource = _resource(client, setup["pm"]).json()
    url = f"/api/resources/{resource['resource_id']}/availability"
    client.post(url, headers=setup["pm"], json={"snapshot_date": "2026-11-01", "availability_pct": 100})

    response = client.post(url, headers=setup["pm"],
                           json={"snapshot_date": "2026-11-14", "availability_pct": 60, "note": "دوام جزئي"})

    assert response.status_code == 201
    assert response.json()["availability_pct"] == 60.0
    assert response.json()["capacity_hours"] == 4.8  # 8 h x 60 %
    history = client.get(url, headers=setup["pm"]).json()
    assert [h["availability_pct"] for h in history] == [60.0, 100.0]
    # Value that rule M2 will read (Queries.sql Q4): latest on or before the date.
    assert float(latest_availability(db, resource["resource_id"], date(2026, 11, 15)).availability_pct) == 60
    assert float(latest_availability(db, resource["resource_id"], date(2026, 11, 13)).availability_pct) == 100
    assert latest_availability(db, resource["resource_id"], date(2026, 10, 31)) is None


@pytest.mark.parametrize("pct", [101, -1])
def test_availability_outside_0_100_returns_422(client, setup, pct):
    resource = _resource(client, setup["pm"]).json()

    response = client.post(f"/api/resources/{resource['resource_id']}/availability", headers=setup["pm"],
                           json={"snapshot_date": "2026-11-01", "availability_pct": pct})

    assert response.status_code == 422
    assert response.json()["fields"][0]["message"] == "نسبة التوفر يجب أن تكون بين 0 و100"


def test_same_date_twice_returns_409(client, setup):
    resource = _resource(client, setup["pm"]).json()
    url = f"/api/resources/{resource['resource_id']}/availability"
    client.post(url, headers=setup["pm"], json={"snapshot_date": "2026-11-01", "availability_pct": 100})

    response = client.post(url, headers=setup["pm"], json={"snapshot_date": "2026-11-01", "availability_pct": 50})

    assert response.status_code == 409 and response.json()["code"] == "DUPLICATE_AVAILABILITY_DATE"


def test_explicit_capacity_hours_is_kept(client, setup):
    resource = _resource(client, setup["pm"]).json()

    response = client.post(f"/api/resources/{resource['resource_id']}/availability", headers=setup["pm"],
                           json={"snapshot_date": "2026-11-01", "availability_pct": 50, "capacity_hours": 3})

    assert response.json()["capacity_hours"] == 3.0


def test_unknown_resource_returns_404(client, setup):
    assert client.get("/api/resources/9999/availability", headers=setup["pm"]).status_code == 404


# --- allocation --------------------------------------------------------------

def test_pm_allocates_resource_to_task_and_can_delete(client, setup, db):
    resource = _resource(client, setup["pm"]).json()
    url = f"/api/resources/{resource['resource_id']}/allocations"

    created = client.post(url, headers=setup["pm"], json={"task_id": setup["task"]["task_id"], "allocated_hours": 40})

    assert created.status_code == 201
    assert created.json()["task_code"] == "T-001" and created.json()["allocated_hours"] == 40.0
    assert [a["task_code"] for a in client.get(url, headers=setup["pm"]).json()] == ["T-001"]
    deleted = client.delete(f"{url}/{created.json()['allocation_id']}", headers=setup["pm"])
    assert deleted.status_code == 204
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.entity_type == "task_allocations")) == 2


def test_planner_member_allocates_but_outside_planner_and_other_pm_get_403(client, setup):
    resource = _resource(client, setup["pm"]).json()
    url = f"/api/resources/{resource['resource_id']}/allocations"
    body = {"task_id": setup["task"]["task_id"], "allocated_hours": 8}

    assert client.post(url, headers=setup["planner_out"], json=body).status_code == 403
    assert client.post(url, headers=setup["pm_other"], json=body).status_code == 403
    assert client.post(url, headers=setup["planner_in"], json=body).status_code == 201


def test_duplicate_allocation_returns_409(client, setup):
    resource = _resource(client, setup["pm"]).json()
    url = f"/api/resources/{resource['resource_id']}/allocations"
    body = {"task_id": setup["task"]["task_id"], "allocated_hours": 8}
    client.post(url, headers=setup["pm"], json=body)

    assert client.post(url, headers=setup["pm"], json=body).status_code == 409


def test_allocation_rejects_zero_hours_unknown_task_and_inactive_resource(client, setup):
    resource = _resource(client, setup["pm"]).json()
    url = f"/api/resources/{resource['resource_id']}/allocations"

    zero = client.post(url, headers=setup["pm"], json={"task_id": setup["task"]["task_id"], "allocated_hours": 0})
    unknown = client.post(url, headers=setup["pm"], json={"task_id": 9999, "allocated_hours": 8})
    client.patch(f"/api/resources/{resource['resource_id']}", headers=setup["pm"], json={"is_active": False})
    inactive = client.post(url, headers=setup["pm"], json={"task_id": setup["task"]["task_id"], "allocated_hours": 8})

    assert zero.status_code == 422 and zero.json()["fields"][0]["field"] == "allocated_hours"
    assert unknown.status_code == 422 and unknown.json()["fields"][0]["field"] == "task_id"
    assert inactive.status_code == 422 and inactive.json()["fields"][0]["field"] == "resource_id"


def test_resource_list_shows_latest_availability_up_to_today(client, setup):
    resource = _resource(client, setup["pm"]).json()
    client.post(f"/api/resources/{resource['resource_id']}/availability", headers=setup["pm"],
                json={"snapshot_date": "2026-01-01", "availability_pct": 70})

    listed = client.get("/api/resources", headers=setup["planner_out"]).json()

    assert listed[0]["latest_availability"]["availability_pct"] == 70.0
