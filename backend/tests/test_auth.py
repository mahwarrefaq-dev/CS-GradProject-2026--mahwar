"""API-01 login, temporary lock and audit (FR-01, NFR-02, SEC-01). Test plan: TC-01, TC-03."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.models import AuditLog, User
from tests.conftest import TEST_PASSWORD


def _actions(db, user_id=None) -> list[str]:
    db.expire_all()
    query = select(AuditLog.action).order_by(AuditLog.audit_id)
    if user_id is not None:
        query = query.where(AuditLog.user_id == user_id)
    return list(db.scalars(query))


def test_tc01_login_success_returns_token_role_and_audit(client, db, make_user):
    user = make_user("pm.demo", "PROJECT_MANAGER")

    response = client.post("/api/auth/login", json={"username": "pm.demo", "password": TEST_PASSWORD})

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["expires_in_minutes"] == 60
    assert body["user"]["role_code"] == "PROJECT_MANAGER"
    assert body["user"]["role_name_ar"] == "مدير المشروع"
    assert _actions(db, user.user_id) == ["login_success"]
    db.refresh(user)
    assert user.last_login_at is not None


def test_wrong_password_returns_401_and_records_login_failed(client, db, make_user):
    user = make_user("pm.demo", "PROJECT_MANAGER")

    response = client.post("/api/auth/login", json={"username": "pm.demo", "password": "wrong-password"})

    assert response.status_code == 401
    assert response.json() == {"code": "INVALID_CREDENTIALS",
                               "message": "اسم المستخدم أو كلمة المرور غير صحيحة", "fields": []}
    assert _actions(db, user.user_id) == ["login_failed"]


def test_unknown_user_gets_same_401_message(client, db):
    response = client.post("/api/auth/login", json={"username": "nobody", "password": "whatever"})

    assert response.status_code == 401
    assert response.json()["message"] == "اسم المستخدم أو كلمة المرور غير صحيحة"
    assert _actions(db) == ["login_failed"]


def test_inactive_user_cannot_login(client, make_user):
    make_user("old.member", "TEAM_MEMBER", is_active=False)

    response = client.post("/api/auth/login", json={"username": "old.member", "password": TEST_PASSWORD})

    assert response.status_code == 401


def test_tc03_account_locked_for_15_minutes_after_fifth_failure(client, db, make_user):
    user = make_user("pm.demo", "PROJECT_MANAGER")
    wrong = {"username": "pm.demo", "password": "wrong-password"}

    codes = [client.post("/api/auth/login", json=wrong).status_code for _ in range(5)]
    sixth_with_correct_password = client.post("/api/auth/login",
                                              json={"username": "pm.demo", "password": TEST_PASSWORD})

    assert codes == [401, 401, 401, 401, 401]
    assert sixth_with_correct_password.status_code == 423
    assert sixth_with_correct_password.json()["code"] == "ACCOUNT_LOCKED"
    db.refresh(user)
    remaining = user.locked_until - datetime.now(timezone.utc)
    assert timedelta(minutes=14) < remaining <= timedelta(minutes=15)
    assert _actions(db, user.user_id) == ["login_failed"] * 6


def test_login_works_again_after_lock_expires(client, db, make_user):
    user = make_user("pm.demo", "PROJECT_MANAGER")
    user.locked_until = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()

    response = client.post("/api/auth/login", json={"username": "pm.demo", "password": TEST_PASSWORD})

    assert response.status_code == 200
    db.refresh(user)
    assert user.locked_until is None and user.failed_login_count == 0


def test_success_resets_failed_counter(client, db, make_user):
    user = make_user("pm.demo", "PROJECT_MANAGER")
    for _ in range(4):
        client.post("/api/auth/login", json={"username": "pm.demo", "password": "wrong-password"})

    client.post("/api/auth/login", json={"username": "pm.demo", "password": TEST_PASSWORD})

    db.refresh(user)
    assert user.failed_login_count == 0 and user.locked_until is None


def test_missing_fields_return_422_with_arabic_field_messages(client):
    response = client.post("/api/auth/login", json={"username": "pm.demo"})

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert {"field": "password", "message": "هذا الحقل مطلوب"} in body["fields"]


def test_request_without_token_returns_401(client):
    response = client.get("/api/users")

    assert response.status_code == 401
    assert response.json()["code"] == "NOT_AUTHENTICATED"


def test_invalid_token_returns_401(client):
    response = client.get("/api/users", headers={"Authorization": "Bearer not-a-token"})

    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_TOKEN"
