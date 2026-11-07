"""Seed master data (idempotent) and optional SYNTHETIC demonstration data.

Usage:
    python -m app.seed.seed            # master data only
    python -m app.seed.seed --demo     # master data + synthetic demo users
"""
from __future__ import annotations

import random
import sys
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import (
    AccessGrant,
    ConsentRecord,
    HabitLog,
    InterviewRecord,
    MicroHabit,
    ScientificReference,
    SystemSetting,
    User,
    UserPreference,
    WellnessAgent,
    WellnessCategory,
    WellnessParameter,
    WellnessRecommendation,
)
from ..security import hash_password
from ..services.agents import REGISTRY
from ..services.assessment import Answer, submit_assessment
from ..services.orchestrator import run_agents
from ..services.reviews import create_review
from . import master_data as md

CONSENT_VERSION = "1.0"
DEMO_PASSWORD = "Demo@1234"


def _upsert(db: Session, model, pk, **values):
    obj = db.get(model, pk)
    if obj is None:
        pk_name = model.__mapper__.primary_key[0].name
        obj = model(**{pk_name: pk}, **values)
        db.add(obj)
    else:
        for k, v in values.items():
            setattr(obj, k, v)
    return obj


def seed_master(db: Session) -> None:
    for order, (cid, name, icon, desc, agent_code) in enumerate(md.CATEGORIES, start=1):
        _upsert(db, WellnessCategory, cid, category_name=name, category_description=desc, category_icon=icon,
                display_order=order, agent_code=agent_code, default_weightage=1.0, target_score=75.0, is_active=True)
    db.flush()
    for cid, questions in md.QUESTIONS.items():
        for i, (pname, question, rtype, reverse, opts) in enumerate(questions, start=1):
            pid = f"{cid}_{i:02d}"
            _upsert(db, WellnessParameter, pid, category_id=cid, parameter_name=pname, parameter_description=question,
                    response_type=rtype, options=opts or md.OPTIONS[rtype],
                    scoring_rule={"method": "linear_1_5_to_0_100", "reverse": reverse},
                    parameter_weightage=1.0, allow_not_applicable=pid in md.NA_ALLOWED, display_order=i, is_active=True)
    for ref in md.REFERENCES:
        rid, cid, title, org, url, pub, level, evidence = ref
        existing = db.get(ScientificReference, rid)
        values = dict(category_id=cid, reference_title=title, issuing_organization=org, reference_url=url,
                      publication_date=pub, evidence_level=level, supporting_evidence=evidence)
        if existing is None:
            values.update(verification_status="pending_verification", last_verified_date=None)
        _upsert(db, ScientificReference, rid, **values)
    for cid, cls in REGISTRY.items():
        _upsert(db, WellnessAgent, cls.agent_id, category_id=cid, agent_name=cls.name,
                agent_description=md.AGENT_DESCRIPTIONS[cid], agent_version=cls.version)
    db.flush()
    for rec in md.RECOMMENDATIONS:
        rid, cid, title, desc, action, habit, freq, ref, targets, prio = rec
        _upsert(db, WellnessRecommendation, rid, category_id=cid, agent_id=REGISTRY[cid].agent_id,
                recommendation_title=title, recommendation_description=desc, recommended_action=action,
                micro_habit=habit, suggested_frequency=freq, evidence_reference=ref, target_parameters=targets,
                recommendation_priority=prio, is_active=True)
    if db.get(SystemSetting, "wellness_levels") is None:
        db.add(SystemSetting(key="wellness_levels", value=md.DEFAULT_LEVELS,
                             description="Provisional application indicators, not clinically validated thresholds."))
    if db.get(SystemSetting, "scoring_config") is None:
        db.add(SystemSetting(key="scoring_config", value=md.DEFAULT_SCORING, description="Scoring engine parameters."))
    db.commit()


def grant_core_consents(db: Session, user: User, ai: bool = True) -> None:
    types = ["data_processing"] + (["ai_analysis"] if ai else [])
    for t in types:
        db.add(ConsentRecord(user_id=user.user_id, consent_type=t, consent_version=CONSENT_VERSION, granted_status=True))


def _user(db: Session, email, name, role, **kw) -> User:
    u = db.scalar(select(User).where(User.email == email))
    if u:
        return u
    u = User(email=email, full_name=name, user_role=role, password_hash=hash_password(DEMO_PASSWORD), is_synthetic=True, **kw)
    db.add(u)
    db.flush()
    db.add(UserPreference(user_id=u.user_id))
    grant_core_consents(db, u)
    return u


def _answers(rng: random.Random, profile: dict[str, float], shift: dict[str, float]) -> list[Answer]:
    out = []
    for cid, qs in md.QUESTIONS.items():
        base = profile.get(cid, 3.0) + shift.get(cid, 0)
        for i, (_, _, rtype, reverse, opts) in enumerate(qs, start=1):
            pid = f"{cid}_{i:02d}"
            v = max(1, min(5, round(base + rng.uniform(-0.8, 0.8))))
            if reverse:
                v = 6 - v
            if rtype == "yes_no":
                v = 5 if v >= 3 else 1
            out.append(Answer(pid, v))
    return out


def seed_demo(db: Session) -> None:
    if db.scalar(select(User).where(User.email == "priya@sampurna.demo")):
        print("Demo data already present.")
        return
    rng = random.Random(42)
    _user(db, "admin@sampurna.demo", "Admin (synthetic)", "admin")
    coach = _user(db, "coach@sampurna.demo", "Anil Mehta (synthetic coach)", "coach", occupation="Wellness coach")
    counselor = _user(db, "counselor@sampurna.demo", "Dr. Kavya Rao (synthetic counsellor)", "counselor", occupation="Counselling psychologist")
    priya = _user(db, "priya@sampurna.demo", "Priya Sharma (synthetic)", "individual", occupation="Software engineer",
                  industry="Information Technology", age_group="30-39", city="Pune")
    ravi = _user(db, "ravi@sampurna.demo", "Ravi Kumar (synthetic)", "individual", occupation="Machine operator",
                 industry="Manufacturing", age_group="40-49", city="Coimbatore")
    db.add(AccessGrant(user_id=priya.user_id, grantee_id=coach.user_id, scopes=["assessments", "interviews", "reports"]))
    db.add(AccessGrant(user_id=priya.user_id, grantee_id=counselor.user_id, scopes=["assessments", "observations", "reports"]))
    db.commit()

    today = date.today()
    q_dates = [datetime.combine(today - timedelta(days=d), datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=10)
               for d in (200, 110, 20)]
    # Priya: stressed IT engineer, gradual improvement; social & sport dip in latest quarter (for cross insights)
    profile = {"MEN": 2.2, "PHY": 2.6, "FIN": 3.4, "PSY": 3.0, "SOC": 3.2, "SPI": 2.8, "FAM": 2.7, "MUS": 3.6,
               "ENV": 3.3, "CIV": 2.3, "EMP": 4.1, "SPO": 3.1, "CUL": 3.5, "UNI": 4.2}
    shifts = [{}, {"MEN": 0.5, "PHY": 0.6, "FAM": 0.4, "SPI": 0.5},
              {"MEN": 0.9, "PHY": 1.0, "FAM": 0.8, "SPI": 0.9, "FIN": 0.3, "SOC": -0.8, "SPO": -0.9}]
    ids = []
    for when, sh in zip(q_dates, shifts):
        s, _ = submit_assessment(db, priya.user_id, _answers(rng, profile, sh), assessment_date=when)
        ids.append(s.assessment_id)
    s, _ = submit_assessment(db, ravi.user_id, _answers(rng, {"FIN": 2.0, "PHY": 3.4, "SOC": 3.8}, {}), assessment_date=q_dates[-1])
    ids.append(s.assessment_id)

    # A cohort of synthetic individuals for anonymised aggregate analytics
    industries = ["Information Technology", "Manufacturing", "Healthcare", "Education"]
    for n in range(12):
        u = _user(db, f"member{n+1}@sampurna.demo", f"Member {n+1} (synthetic)", "individual",
                  industry=industries[n % 4], occupation="Professional", age_group=["20-29", "30-39", "40-49"][n % 3], city="Bengaluru")
        prof = {c[0]: rng.uniform(2.0, 4.3) for c in md.CATEGORIES}
        s, _ = submit_assessment(db, u.user_id, _answers(rng, prof, {}), assessment_date=q_dates[-1] - timedelta(days=n))
        ids.append(s.assessment_id)
    db.commit()

    for aid in ids:
        run_agents(aid)
    create_review(db, priya.user_id, coach_id=coach.user_id)

    habits = [("MEN", "REC_MEN_1", "Take a short mindful break", "daily", 1), ("PHY", "REC_PHY_1", "A 10-minute brisk walk", "daily", 1),
              ("FAM", "REC_FAM_1", "Phone-free family conversation", "daily", 1), ("SOC", "REC_SOC_1", "Connect with a friend or relative", "weekly", 1)]
    for cid, rid, name, freq, tgt in habits:
        h = MicroHabit(user_id=priya.user_id, category_id=cid, recommendation_id=rid, habit_name=name, frequency=freq,
                       target_frequency=tgt, start_date=today - timedelta(days=84), reminder_time="19:00")
        db.add(h)
        db.flush()
        for d in range(84):
            day = today - timedelta(days=d)
            p = 0.75 if freq == "daily" else 0.12
            if rng.random() < p * (0.6 + 0.4 * (84 - d) / 84):
                db.add(HabitLog(habit_id=h.habit_id, log_date=day))
                h.completion_count += 1
    db.add(InterviewRecord(user_id=priya.user_id, interviewer_id=coach.user_id, assessment_id=ids[1],
                           interview_date=q_dates[1] + timedelta(days=2), status="completed",
                           observations={"MEN": "Describes frequent late-evening calls; keen to set boundaries.", "FAM": "Wants more time with daughter."},
                           interview_summary="Discussed work boundaries and family time. Agreed on end-of-work routine and two family dinners per week.",
                           summary_source="interviewer", consent_status="not_requested",
                           follow_up_plan="End-of-work routine; phone-free dinners", follow_up_date=(q_dates[1] + timedelta(days=45)).date()))
    db.commit()
    print(f"Synthetic demo data created. Log in with any *@sampurna.demo account, password {DEMO_PASSWORD}")


def main() -> None:
    with SessionLocal() as db:
        seed_master(db)
        print("Master data seeded: 14 categories, 56 parameters, references, agents, recommendations.")
        if "--demo" in sys.argv:
            seed_demo(db)


if __name__ == "__main__":
    main()
