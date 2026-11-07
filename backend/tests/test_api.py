"""API and end-to-end user-journey tests (against PostgreSQL)."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.models import AgentAssessment, AssessmentSession, AuditLog
from tests.conftest import all_answers, make_staff, register


def test_registration_requires_consent(client):
    r = client.post("/api/auth/register", json={"full_name": "No Consent", "email": "nc@example.com", "password": "Passw0rd!",
                                               "consent_data_processing": False})
    assert r.status_code == 400


def test_login_and_me(client):
    h, u = register(client)
    r = client.post("/api/auth/login", json={"email": u["email"], "password": "Passw0rd!"})
    assert r.status_code == 200
    assert client.get("/api/auth/me", headers=h).json()["email"] == u["email"]
    assert client.post("/api/auth/login", json={"email": u["email"], "password": "wrong"}).status_code == 401
    assert client.get("/api/dashboard").status_code == 401


def test_master_data(client):
    h, _ = register(client)
    cats = client.get("/api/categories", headers=h).json()
    assert len(cats) == 14
    assert all(3 <= len(c["parameters"]) <= 4 for c in cats)
    assert sum(len(c["parameters"]) for c in cats) == 56
    assert len(client.get("/api/agents", headers=h).json()) == 14
    recs = client.get("/api/recommendations", headers=h).json()
    assert recs and all(r["evidence"] and r["evidence"]["url"].startswith("https://") for r in recs)
    assert {r["category_id"] for r in recs} == {c["category_id"] for c in cats}


def test_full_individual_journey(client, db):
    h, user = register(client)
    # 1. self-assessment with NA + prefer-not answers
    answers = all_answers(client, h, 3, {"MEN": 2, "UNI": 5})
    for a in answers:
        if a["parameter_id"] == "FIN_02":
            a.update(value=None, status="not_applicable")
        if a["parameter_id"] == "SOC_02":
            a.update(value=None, status="prefer_not_to_answer")
    r = client.post("/api/assessments", json={"answers": answers}, headers=h)
    assert r.status_code == 201, r.text
    a1 = r.json()
    assert a1["assessment_type"] == "baseline"
    assert len(a1["scores"]) == 14 and a1["overall_indicator"] is not None
    assert a1["safety"] is None

    # 2. all 14 agents executed (background task) and stored results
    res = client.get(f"/api/assessments/{a1['assessment_id']}/agents", headers=h).json()
    assert res["agents_status"] == "completed"
    assert len(res["results"]) == 14
    for out in res["results"]:
        for key in ("user_id", "assessment_id", "category_id", "current_score", "current_level", "target_level", "strengths",
                    "improvement_areas", "recommended_actions", "suggested_micro_habits", "evidence_references",
                    "confidence_level", "review_interval_days"):
            assert key in out
        for act in out["recommended_actions"]:
            assert act["evidence_reference"] in {e["reference_id"] for e in out["evidence_references"]}
    fin = next(o for o in res["results"] if o["category_id"] == "FIN")
    assert fin["coverage"] == 0.75  # NA excluded from coverage numerator
    assert any("No current loans" in n for n in fin["specialised_notes"])

    # 3. dashboard reflects DB records
    d = client.get("/api/dashboard", headers=h).json()
    assert d["has_data"] and len(d["cards"]) == 14 and len(d["radar"]) == 14
    men = next(c for c in d["cards"] if c["category_id"] == "MEN")
    assert men["current"] == 37.5 and men["level"] == "Needs Attention"  # (75 reverse-scored stress + 25×3) / 4
    assert any(f["category_id"] == "MEN" for f in d["attention_flags"])
    assert d["overview"]["dimensions_assessed"] == 14

    # 4. micro-habits
    hb = client.post("/api/habits", json={"category_id": "MEN", "habit_name": "Mindful break", "frequency": "daily"}, headers=h).json()
    client.post(f"/api/habits/{hb['habit_id']}/log", json={}, headers=h)
    again = client.post(f"/api/habits/{hb['habit_id']}/log", json={}, headers=h).json()
    assert again["completion_count"] == 1 and again["done_today"]  # idempotent per day
    undone = client.delete(f"/api/habits/{hb['habit_id']}/log", headers=h).json()
    assert undone["completion_count"] == 0
    upd = client.patch(f"/api/habits/{hb['habit_id']}", json={"frequency": "weekly", "user_feedback": "easier weekly"}, headers=h).json()
    assert upd["frequency"] == "weekly"

    # 5. plan from recommendation creates a habit
    p = client.post("/api/plans", json={"recommendation_id": "REC_PHY_1"}, headers=h)
    assert p.status_code == 201
    assert any(x["recommendation_id"] == "REC_PHY_1" for x in client.get("/api/habits", headers=h).json())

    # 6. quarterly reassessment preserves history and shows genuine change
    r2 = client.post("/api/assessments", json={"answers": all_answers(client, h, 4, {"MEN": 4})}, headers=h).json()
    assert r2["assessment_type"] == "quarterly"
    lst = client.get("/api/assessments", headers=h).json()
    assert len(lst) == 2
    first = client.get(f"/api/assessments/{a1['assessment_id']}", headers=h).json()
    assert next(s for s in first["scores"] if s["category_id"] == "MEN")["score"] == 37.5  # untouched
    rev = client.post("/api/reviews", headers=h).json()
    row = next(x for x in rev["comparison"]["rows"] if x["category_id"] == "MEN")
    assert row["baseline"] == 37.5 and row["current"] == 62.5 and row["change"] == 25.0 and row["direction"] == "improved"
    assert client.post("/api/reviews", headers=h).json()["review_id"] == rev["review_id"]  # idempotent per assessment

    # 7. PDF report
    pdf = client.get("/api/reports/pdf", headers=h)
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"

    # 8. data export
    exp = client.get("/api/me/export", headers=h).json()
    assert len(exp["assessments"]) == 2


def test_reverse_scoring_math(client):
    h, _ = register(client)
    # MEN_01 (stress, reverse) answered 2 = "occasionally stressed" -> 75; others answered 2 -> 25
    ans = [{"parameter_id": p, "value": 2} for p in ("MEN_01", "MEN_02", "MEN_03", "MEN_04")]
    r = client.post("/api/assessments", json={"answers": ans}, headers=h).json()
    men = next(s for s in r["scores"] if s["category_id"] == "MEN")
    assert men["score"] == round((75 + 25 + 25 + 25) / 4, 1)
    assert r["overall_indicator"] is None  # only 1 category assessed -> no overall
    other = next(s for s in r["scores"] if s["category_id"] == "PHY")
    assert other["score"] is None and other["level"] == "Insufficient data"


def test_invalid_submission_is_atomic(client, db):
    h, user = register(client)
    before = db.query(AssessmentSession).count()
    bad = [{"parameter_id": "MEN_01", "value": 3}, {"parameter_id": "NOPE_99", "value": 3}]
    assert client.post("/api/assessments", json={"answers": bad}, headers=h).status_code == 422
    na_not_allowed = [{"parameter_id": "MEN_01", "status": "not_applicable"}]
    assert client.post("/api/assessments", json={"answers": na_not_allowed}, headers=h).status_code == 422
    assert db.query(AssessmentSession).count() == before


def test_crisis_language_triggers_guidance(client):
    h, _ = register(client)
    r = client.post("/api/assessments", json={"answers": all_answers(client, h, 2),
                                              "category_comments": {"MEN": "I feel hopeless and want to end it all"}}, headers=h).json()
    assert r["safety"] and any("14416" in x["contact"] for x in r["safety"]["resources"])
    agents = client.get(f"/api/assessments/{r['assessment_id']}/agents", headers=h).json()["results"]
    assert next(a for a in agents if a["category_id"] == "MEN")["safety"] is not None


def test_coach_access_requires_consent(client, db):
    h, user = register(client)
    client.post("/api/assessments", json={"answers": all_answers(client, h, 3)}, headers=h)
    ch, coach_id = make_staff("coach")
    uid = user["user_id"]
    # no grant -> denied, and audited
    assert client.get(f"/api/dashboard?user_id={uid}", headers=ch).status_code == 403
    assert client.get(f"/api/assessments?user_id={uid}", headers=ch).status_code == 403
    assert client.get("/api/coach/clients", headers=ch).json() == []
    assert db.scalar(select(AuditLog).where(AuditLog.action == "access_denied", AuditLog.subject_user_id == user["user_id"]))
    # grant
    g = client.post("/api/access-grants", json={"grantee_id": coach_id, "scopes": ["assessments", "interviews", "reports"]}, headers=h)
    assert g.status_code == 201
    assert client.get(f"/api/dashboard?user_id={uid}", headers=ch).status_code == 200
    assert len(client.get("/api/coach/clients", headers=ch).json()) == 1
    assert client.get(f"/api/reports/pdf?user_id={uid}&kind=coach", headers=ch).status_code == 200
    # another coach still denied
    ch2, _ = make_staff("coach")
    assert client.get(f"/api/dashboard?user_id={uid}", headers=ch2).status_code == 403
    # revoke
    client.delete(f"/api/access-grants/{g.json()['grant_id']}", headers=h)
    assert client.get(f"/api/dashboard?user_id={uid}", headers=ch).status_code == 403


def test_admin_cannot_see_individual_data(client):
    h, user = register(client)
    client.post("/api/assessments", json={"answers": all_answers(client, h, 3)}, headers=h)
    ah, _ = make_staff("admin")
    assert client.get("/api/dashboard", headers=ah).status_code == 403
    assert client.get(f"/api/dashboard?user_id={user['user_id']}", headers=ah).status_code == 403
    users = client.get("/api/admin/users", headers=ah).json()
    assert users and "scores" not in users[0]
    a = client.get("/api/admin/analytics?group_by=industry", headers=ah).json()
    assert all(g["people"] >= a["min_group_size"] for g in a["groups"])
    # individuals can't reach admin
    assert client.get("/api/admin/users", headers=h).status_code == 403


def test_analytics_suppresses_small_groups(client):
    h, _ = register(client, industry="TinyIndustryXYZ")
    client.post("/api/assessments", json={"answers": all_answers(client, h, 3)}, headers=h)
    ah, _ = make_staff("admin")
    a = client.get("/api/admin/analytics?group_by=industry", headers=ah).json()
    assert "TinyIndustryXYZ" not in {g["group"] for g in a["groups"]}
    assert a["suppressed_groups"] >= 1


def test_interview_assessment_and_transcript_consent(client):
    h, user = register(client)
    ch, coach_id = make_staff("coach")
    uid = user["user_id"]
    body = {"user_id": uid, "answers": all_answers(client, h, 4), "observations": {"MEN": "Calm and reflective"},
            "transcript": "Coach: How are you? Client: Better."}
    assert client.post("/api/interviews", json=body, headers=ch).status_code == 403  # no grant
    client.post("/api/access-grants", json={"grantee_id": coach_id, "scopes": ["assessments", "interviews"]}, headers=h)
    assert client.post("/api/interviews", json=body, headers=ch).status_code == 403  # no transcription consent
    client.post("/api/consents", json={"consent_type": "interview_transcription", "granted": True}, headers=h)
    r = client.post("/api/interviews", json=body, headers=ch)
    assert r.status_code == 201, r.text
    iv = r.json()
    assert iv["assessment"]["assessment_source"] == "interview"
    assert iv["interview"]["has_transcript"]
    iid = iv["interview"]["interview_id"]
    assert client.get(f"/api/interviews/{iid}/transcript", headers=h).json()["transcript"].startswith("Coach:")
    draft = client.post(f"/api/interviews/{iid}/ai-summary", headers=ch).json()
    assert "Draft" in draft["draft"] or "draft" in draft["label"]
    # AI draft does not alter answers
    a = client.get(f"/api/assessments/{iv['assessment']['assessment_id']}", headers=h).json()
    assert all(r["value"] in (4, 5) for r in a["responses"])
    assert len(client.get("/api/interviews", headers=h).json()) == 1


def test_consent_withdrawal_and_account_deletion(client):
    h, user = register(client)
    c = client.post("/api/consents", json={"consent_type": "ai_analysis", "granted": False}, headers=h).json()
    assert c["ai_analysis"]["granted"] is False
    assert client.delete("/api/me", headers=h).json()["status"] == "deleted"
    assert client.get("/api/auth/me", headers=h).status_code == 401


def test_independent_single_agent_execution(client, db):
    h, _ = register(client)
    a = client.post("/api/assessments", json={"answers": all_answers(client, h, 3)}, headers=h).json()
    out = client.post(f"/api/agents/financial_agent/run?assessment_id={a['assessment_id']}", headers=h)
    assert out.status_code == 200 and out.json()["category_id"] == "FIN"
    rows = db.scalars(select(AgentAssessment).where(AgentAssessment.assessment_id == a["assessment_id"])).all()
    assert len(rows) == 14  # re-run upserts, no duplicates


def test_notifications_reminders(client):
    h, _ = register(client)
    n = client.get("/api/notifications", headers=h).json()
    assert any(x["type"] == "assessment_due" for x in n)
    assert len(client.get("/api/notifications", headers=h).json()) == len(n)  # deduplicated
