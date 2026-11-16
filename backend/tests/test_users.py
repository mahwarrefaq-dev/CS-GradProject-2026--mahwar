"""API-02 /api/users (FR-01, NFR-02): system administrator only, duplicate name 409, audit."""
from sqlalchemy import select

from app.models import AuditLog, User


def _audit(db, action: str) -> list[AuditLog]:
    db.expire_all()
    return list(db.scalars(select(AuditLog).where(AuditLog.action == action).order_by(AuditLog.audit_id)))


def test_admin_creates_user_and_create_is_audited(client, db, make_user, auth_headers):
    make_user("admin.demo", "SYSTEM_ADMIN")
    headers = auth_headers("admin.demo")

    response = client.post("/api/users", headers=headers, json={
        "username": "member.x", "display_alias": "عضو-س", "password": "Member#2026", "role_code": "TEAM_MEMBER"})

    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "member.x" and body["role_code"] == "TEAM_MEMBER" and body["is_active"] is True
    assert "password_hash" not in body
    created = _audit(db, "create")
    assert len(created) == 1 and created[0].entity_id == str(body["user_id"])
    assert client.post("/api/auth/login", json={"username": "member.x", "password": "Member#2026"}).status_code == 200


def test_duplicate_username_returns_409(client, make_user, auth_headers):
    make_user("admin.demo", "SYSTEM_ADMIN")
    make_user("member.x", "TEAM_MEMBER")

    response = client.post("/api/users", headers=auth_headers("admin.demo"), json={
        "username": "member.x", "display_alias": "مكرر", "password": "Member#2026", "role_code": "TEAM_MEMBER"})

    assert response.status_code == 409
    assert response.json()["code"] == "DUPLICATE_USERNAME"


def test_invalid_username_and_role_return_422_with_fields(client, make_user, auth_headers):
    make_user("admin.demo", "SYSTEM_ADMIN")

    response = client.post("/api/users", headers=auth_headers("admin.demo"), json={
        "username": "Ahmed Ali", "display_alias": "x", "password": "short", "role_code": "BOSS"})

    assert response.status_code == 422
    fields = {f["field"] for f in response.json()["fields"]}
    assert fields == {"username", "password", "role_code"}


def test_non_admin_gets_403_and_access_denied_is_audited(client, db, make_user, auth_headers):
    pm = make_user("pm.demo", "PROJECT_MANAGER")

    response = client.get("/api/users", headers=auth_headers("pm.demo"))

    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"
    denied = _audit(db, "access_denied")
    assert len(denied) == 1 and denied[0].user_id == pm.user_id


def test_role_change_is_audited_as_role_change(client, db, make_user, auth_headers):
    make_user("admin.demo", "SYSTEM_ADMIN")
    member = make_user("member.x", "TEAM_MEMBER")

    response = client.patch(f"/api/users/{member.user_id}", headers=auth_headers("admin.demo"),
                            json={"role_code": "PLANNER"})

    assert response.status_code == 200 and response.json()["role_code"] == "PLANNER"
    changes = _audit(db, "role_change")
    assert len(changes) == 1
    assert changes[0].old_value == {"role_code": "TEAM_MEMBER"}
    assert changes[0].new_value == {"role_code": "PLANNER"}


def test_deactivated_user_token_is_rejected(client, db, make_user, auth_headers):
    make_user("admin.demo", "SYSTEM_ADMIN")
    member = make_user("member.x", "TEAM_MEMBER")
    member_headers = auth_headers("member.x")

    client.patch(f"/api/users/{member.user_id}", headers=auth_headers("admin.demo"), json={"is_active": False})

    assert client.get("/api/users", headers=member_headers).status_code == 401
    db.expire_all()
    assert db.get(User, member.user_id).is_active is False


def test_patch_unknown_user_returns_404(client, make_user, auth_headers):
    make_user("admin.demo", "SYSTEM_ADMIN")

    response = client.patch("/api/users/9999", headers=auth_headers("admin.demo"), json={"display_alias": "x"})

    assert response.status_code == 404
