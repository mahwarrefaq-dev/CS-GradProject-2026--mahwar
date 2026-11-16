"""Integration-test fixtures (Chapter 4, Table 4.21: pytest + FastAPI test client + test database).

Every test that uses `client` gets a fresh `mahwar_test` schema rebuilt from
database/Schema_Script.sql, so the development database is never touched.
"""
from collections.abc import Callable, Iterator
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.config import settings
from app.database import get_db
from app.main import app
from app.models import Role, User
from app.security import hash_password

SCHEMA_SCRIPT = Path(__file__).resolve().parents[2] / "database" / "Schema_Script.sql"
TEST_PASSWORD = "Passw0rd!test"


@pytest.fixture(scope="session")
def test_engine():
    if not settings.test_database_url:
        pytest.skip("TEST_DATABASE_URL is not set in backend/.env")
    engine = create_engine(settings.test_database_url, poolclass=NullPool)
    yield engine
    engine.dispose()


def _rebuild_schema() -> None:
    url = settings.test_database_url.replace("postgresql+psycopg://", "postgresql://")
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute("DROP SCHEMA IF EXISTS public CASCADE")
        conn.execute("CREATE SCHEMA public")
        conn.execute(SCHEMA_SCRIPT.read_text(encoding="utf-8"))


@pytest.fixture
def session_factory(test_engine) -> sessionmaker:
    _rebuild_schema()
    return sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)


@pytest.fixture
def db(session_factory) -> Iterator[Session]:
    session = session_factory()
    yield session
    session.close()


@pytest.fixture
def client(session_factory) -> Iterator[TestClient]:
    def _get_test_db() -> Iterator[Session]:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _get_test_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def make_user(db) -> Callable[..., User]:
    def _make(username: str, role_code: str, password: str = TEST_PASSWORD, is_active: bool = True) -> User:
        role = db.scalar(select(Role).where(Role.role_code == role_code))
        user = User(username=username, display_alias=username, password_hash=hash_password(password),
                    role_id=role.role_id, is_active=is_active)
        db.add(user)
        db.commit()
        return user

    return _make


@pytest.fixture
def auth_headers(client) -> Callable[[str], dict]:
    def _headers(username: str, password: str = TEST_PASSWORD) -> dict:
        response = client.post("/api/auth/login", json={"username": username, "password": password})
        assert response.status_code == 200, response.text
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    return _headers
