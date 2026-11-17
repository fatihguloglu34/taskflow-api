import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app

engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)
TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def register(client):
    def _register(email="ali@example.com", password="password123", full_name="Ali Veli"):
        r = client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password, "full_name": full_name},
        )
        assert r.status_code == 201, r.text
        token = client.post(
            "/api/v1/auth/login", data={"username": email, "password": password}
        ).json()["access_token"]
        return {"id": r.json()["id"], "headers": {"Authorization": f"Bearer {token}"}}

    return _register


@pytest.fixture
def project(client, register):
    owner = register()
    r = client.post("/api/v1/projects", json={"name": "Demo"}, headers=owner["headers"])
    return {"id": r.json()["id"], "owner": owner}
