"""Database integrity, orchestration resilience and migration tests."""
import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.models import AgentExecutionLog, AssessmentResponse, AssessmentSession, User
from app.services import agents as agents_mod
from app.services.assessment import Answer, submit_assessment
from app.services.orchestrator import run_agents


def _user(db):
    u = User(full_name="Integrity", email=f"i{uuid.uuid4().hex[:8]}@example.com", password_hash="x")
    db.add(u)
    db.commit()
    return u


def test_fk_prevents_orphan_response(db):
    db.add(AssessmentResponse(assessment_id=uuid.uuid4(), parameter_id="MEN_01", response_value=3))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_check_constraint_on_response_value(db):
    u = _user(db)
    s, _ = submit_assessment(db, u.user_id, [Answer("MEN_01", 3)])
    db.add(AssessmentResponse(assessment_id=s.assessment_id, parameter_id="MEN_02", response_value=9))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    db.add(AssessmentResponse(assessment_id=s.assessment_id, parameter_id="MEN_02", response_value=3, response_status="not_applicable"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_unique_response_per_parameter(db):
    u = _user(db)
    s, _ = submit_assessment(db, u.user_id, [Answer("MEN_01", 3)])
    db.add(AssessmentResponse(assessment_id=s.assessment_id, parameter_id="MEN_01", response_value=4))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_user_with_assessments_cannot_be_hard_deleted(db):
    u = _user(db)
    submit_assessment(db, u.user_id, [Answer("MEN_01", 3)])
    with pytest.raises(IntegrityError):
        db.execute(text("delete from users where user_id = :u"), {"u": u.user_id})
        db.commit()
    db.rollback()


def test_agents_retry_and_log(db, monkeypatch):
    u = _user(db)
    s, _ = submit_assessment(db, u.user_id, [Answer(f"{c}_0{i}", 3) for c in ("MEN", "PHY") for i in (1, 2, 3, 4)])
    calls = {"n": 0}
    original = agents_mod.SocialWellnessAgent.run

    def flaky(self, db_, aid):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("transient failure")
        return original(self, db_, aid)

    monkeypatch.setattr(agents_mod.SocialWellnessAgent, "run", flaky)
    result = run_agents(s.assessment_id)
    assert result["status"] == "completed"
    assert result["agents"]["social_agent"]["status"] == "succeeded"
    logs = db.scalars(select(AgentExecutionLog).where(AgentExecutionLog.assessment_id == s.assessment_id,
                                                      AgentExecutionLog.agent_id == "social_agent")).all()
    assert sorted(l.status for l in logs) == ["failed", "succeeded"]


def test_permanent_failure_isolated(db, monkeypatch):
    u = _user(db)
    s, _ = submit_assessment(db, u.user_id, [Answer("MEN_01", 3), Answer("MEN_02", 3)])
    monkeypatch.setattr(agents_mod.MusicalWellnessAgent, "run", lambda *a: (_ for _ in ()).throw(RuntimeError("down")))
    monkeypatch.setattr("app.services.orchestrator.time.sleep", lambda *_: None)
    result = run_agents(s.assessment_id)
    assert result["status"] == "partial"
    assert result["agents"]["musical_agent"]["status"] == "failed"
    assert sum(1 for v in result["agents"].values() if v["status"] == "succeeded") == 13
    db.expire_all()
    assert db.get(AssessmentSession, s.assessment_id).agents_status == "partial"


def test_each_agent_runs_independently(db):
    u = _user(db)
    s, _ = submit_assessment(db, u.user_id, [Answer("SPO_01", 5), Answer("SPO_02", 4)])
    for cid in agents_mod.REGISTRY:
        out = agents_mod.get_agent(cid).run(db, s.assessment_id)
        assert out["category_id"] == cid
    assert agents_mod.get_agent("SPO").run(db, s.assessment_id)["current_score"] == 87.5


def test_alembic_migration_matches_models():
    """Upgrade a scratch schema and compare with the ORM metadata."""
    from alembic import command
    from alembic.autogenerate import compare_metadata
    from alembic.config import Config
    from alembic.migration import MigrationContext
    from sqlalchemy import create_engine
    import os

    url = os.environ["DATABASE_URL"].rsplit("/", 1)[0] + "/swasti_migtest"
    admin = create_engine(os.environ["DATABASE_URL"].rsplit("/", 1)[0] + "/postgres", isolation_level="AUTOCOMMIT")
    with admin.connect() as c:
        c.execute(text("drop database if exists swasti_migtest"))
        c.execute(text("create database swasti_migtest"))
    os.environ["DATABASE_URL_MIG"] = url
    from app.config import get_settings
    cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(os.path.dirname(__file__), "..", "migrations"))
    old = get_settings().database_url
    get_settings().database_url = url
    try:
        command.upgrade(cfg, "head")
    finally:
        get_settings().database_url = old
    from app.database import Base
    eng = create_engine(url)
    with eng.connect() as c:
        diff = compare_metadata(MigrationContext.configure(c), Base.metadata)
    eng.dispose()
    assert diff == []
