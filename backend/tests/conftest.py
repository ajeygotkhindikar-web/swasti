import os

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://postgres@localhost:5432/sampurna_test")
os.environ.pop("ANTHROPIC_API_KEY", None)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.seed.seed import seed_master  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed_master(db)
    yield


@pytest.fixture
def db():
    with SessionLocal() as s:
        yield s


@pytest.fixture
def client():
    return TestClient(app)


_n = [0]


def register(client, consent_ai=True, **kw):
    _n[0] += 1
    body = {"full_name": f"Test User {_n[0]}", "email": f"user{_n[0]}_{os.getpid()}@example.com", "password": "Passw0rd!",
            "consent_data_processing": True, "consent_ai_analysis": consent_ai, "industry": "Testing"} | kw
    r = client.post("/api/auth/register", json=body)
    assert r.status_code == 201, r.text
    data = r.json()
    return {"Authorization": f"Bearer {data['access_token']}"}, data["user"]


def make_staff(role):
    from app.models import User
    from app.security import create_token, hash_password
    _n[0] += 1
    with SessionLocal() as s:
        u = User(full_name=f"{role} {_n[0]}", email=f"{role}{_n[0]}_{os.getpid()}@example.com", password_hash=hash_password("x" * 8), user_role=role)
        s.add(u)
        s.commit()
        return {"Authorization": f"Bearer {create_token(u)}"}, str(u.user_id)


def all_answers(client, headers, value=3, overrides=None):
    cats = client.get("/api/categories", headers=headers).json()
    overrides = overrides or {}
    out = []
    for c in cats:
        for p in c["parameters"]:
            v = overrides.get(p["parameter_id"], overrides.get(c["category_id"], value))
            if p["response_type"] == "yes_no":
                v = 5 if v >= 3 else 1
            out.append({"parameter_id": p["parameter_id"], "value": v})
    return out
