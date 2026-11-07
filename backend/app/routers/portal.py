"""Coach / counsellor portal and administration."""
import uuid
from collections import defaultdict
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..models import (
    AccessGrant,
    AgentExecutionLog,
    AssessmentSession,
    AuditLog,
    InterviewRecord,
    ProfessionalObservation,
    ScientificReference,
    SystemSetting,
    User,
    UserPreference,
    WellnessAgent,
    WellnessCategory,
    WellnessCategoryScore,
    WellnessParameter,
)
from ..security import hash_password, require_roles
from ..services.access import active_grant, ensure_can_view
from ..services.audit import audit
from ..services.dashboard import build_dashboard
from ..services.reviews import generate_notifications
from .auth import user_out

router = APIRouter(tags=["Coach & Counsellor Portal"])
admin = APIRouter(prefix="/admin", tags=["Administration"])


# ============================================================ coach portal
@router.get("/coach/clients")
def clients(actor: User = Depends(require_roles("coach", "counselor")), db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    grants = db.scalars(select(AccessGrant).where(AccessGrant.grantee_id == actor.user_id, AccessGrant.status == "active")).all()
    out = []
    for g in grants:
        if g.expires_at and g.expires_at <= now:
            continue
        u = db.get(User, g.user_id)
        if u.account_status != "active":
            continue
        item = {"user_id": str(u.user_id), "full_name": u.full_name, "occupation": u.occupation, "city": u.city,
                "scopes": g.scopes, "granted_at": g.granted_at.isoformat(), "is_synthetic": u.is_synthetic}
        if "assessments" in g.scopes:
            d = build_dashboard(db, u.user_id)
            item["overview"] = d["overview"]
            item["attention_flags"] = d["attention_flags"]
        last_iv = db.scalar(select(InterviewRecord).where(InterviewRecord.user_id == u.user_id, InterviewRecord.interviewer_id == actor.user_id)
                            .order_by(InterviewRecord.interview_date.desc()).limit(1))
        item["last_interview"] = last_iv.interview_date.isoformat() if last_iv else None
        item["next_follow_up"] = last_iv.follow_up_date.isoformat() if last_iv and last_iv.follow_up_date else None
        out.append(item)
    return out


class ObservationIn(BaseModel):
    user_id: uuid.UUID
    category_id: str | None = None
    observation: str = Field(min_length=2, max_length=5000)
    referral_recommended: bool = False
    referral_note: str | None = None
    follow_up_date: date | None = None


@router.post("/counselor/observations", status_code=201)
def add_observation(body: ObservationIn, actor: User = Depends(require_roles("counselor")), db: Session = Depends(get_db)):
    ensure_can_view(db, actor, body.user_id, "observations")
    o = ProfessionalObservation(counselor_id=actor.user_id, **body.model_dump())
    db.add(o)
    db.commit()
    return {"observation_id": str(o.observation_id)}


@router.get("/counselor/observations")
def list_observations(user_id: uuid.UUID, actor: User = Depends(require_roles("counselor")), db: Session = Depends(get_db)):
    ensure_can_view(db, actor, user_id, "observations")
    db.commit()
    rows = db.scalars(select(ProfessionalObservation).where(ProfessionalObservation.user_id == user_id, ProfessionalObservation.counselor_id == actor.user_id)
                      .order_by(ProfessionalObservation.created_at.desc()))
    return [{"observation_id": str(o.observation_id), "category_id": o.category_id, "observation": o.observation,
             "referral_recommended": o.referral_recommended, "referral_note": o.referral_note,
             "follow_up_date": o.follow_up_date.isoformat() if o.follow_up_date else None, "created_at": o.created_at.isoformat()} for o in rows]


# ============================================================ administration
AdminDep = Depends(require_roles("admin"))


class CategoryPatch(BaseModel):
    category_description: str | None = None
    default_weightage: float | None = Field(default=None, ge=0, le=5)
    target_score: float | None = Field(default=None, ge=0, le=100)
    is_active: bool | None = None


class ParameterPatch(BaseModel):
    parameter_description: str | None = None
    parameter_weightage: float | None = Field(default=None, gt=0, le=5)
    allow_not_applicable: bool | None = None
    is_active: bool | None = None


class AgentPatch(BaseModel):
    status: str | None = Field(default=None, pattern="^(active|disabled)$")
    execution_mode: str | None = Field(default=None, pattern="^(parallel|sequential)$")


class SettingPut(BaseModel):
    value: dict | list


class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str = Field(min_length=8)
    user_role: str = Field(pattern="^(individual|coach|counselor|admin)$")
    occupation: str | None = None


class UserPatch(BaseModel):
    user_role: str | None = Field(default=None, pattern="^(individual|coach|counselor|admin)$")
    account_status: str | None = Field(default=None, pattern="^(active|suspended)$")


@admin.get("/categories")
def admin_categories(_: User = AdminDep, db: Session = Depends(get_db)):
    return [{"category_id": c.category_id, "category_name": c.category_name, "description": c.category_description,
             "weightage": c.default_weightage, "target_score": c.target_score, "is_active": c.is_active, "icon": c.category_icon,
             "parameters": [{"parameter_id": p.parameter_id, "name": p.parameter_name, "question": p.parameter_description,
                             "response_type": p.response_type, "weightage": p.parameter_weightage,
                             "reverse": p.scoring_rule.get("reverse"), "allow_not_applicable": p.allow_not_applicable,
                             "is_active": p.is_active} for p in c.parameters]}
            for c in db.scalars(select(WellnessCategory).order_by(WellnessCategory.display_order))]


@admin.patch("/categories/{category_id}")
def patch_category(category_id: str, body: CategoryPatch, actor: User = AdminDep, db: Session = Depends(get_db)):
    c = db.get(WellnessCategory, category_id)
    if c is None:
        raise HTTPException(404, "Not found")
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(c, k, v)
    audit(db, actor.user_id, "admin_category_updated", None, category_id, data)
    db.commit()
    return {"ok": True}


@admin.patch("/parameters/{parameter_id}")
def patch_parameter(parameter_id: str, body: ParameterPatch, actor: User = AdminDep, db: Session = Depends(get_db)):
    p = db.get(WellnessParameter, parameter_id)
    if p is None:
        raise HTTPException(404, "Not found")
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(p, k, v)
    audit(db, actor.user_id, "admin_parameter_updated", None, parameter_id, data)
    db.commit()
    return {"ok": True}


@admin.get("/settings")
def get_settings_(_: User = AdminDep, db: Session = Depends(get_db)):
    return {s.key: {"value": s.value, "description": s.description} for s in db.scalars(select(SystemSetting))}


@admin.put("/settings/{key}")
def put_setting(key: str, body: SettingPut, actor: User = AdminDep, db: Session = Depends(get_db)):
    if key not in ("wellness_levels", "scoring_config"):
        raise HTTPException(404, "Unknown setting")
    if key == "wellness_levels":
        bands = body.value
        if not isinstance(bands, list) or not bands or any({"min", "max", "level"} - set(b) for b in bands):
            raise HTTPException(422, "wellness_levels must be a list of {min,max,level,color}")
        bands = sorted(bands, key=lambda b: b["min"])
        if bands[0]["min"] != 0 or bands[-1]["max"] != 100 or any(b["min"] > b["max"] for b in bands):
            raise HTTPException(422, "Bands must cover 0–100 in order")
        body.value = bands
    row = db.get(SystemSetting, key)
    row.value = body.value
    audit(db, actor.user_id, "admin_setting_updated", None, key, {"value": body.value})
    db.commit()
    return {"key": key, "value": row.value}


@admin.patch("/references/{reference_id}")
def verify_reference(reference_id: str, verified: bool = True, actor: User = AdminDep, db: Session = Depends(get_db)):
    r = db.get(ScientificReference, reference_id)
    if r is None:
        raise HTTPException(404, "Not found")
    r.verification_status = "verified" if verified else "needs_review"
    r.last_verified_date = date.today() if verified else None
    audit(db, actor.user_id, "reference_verification", None, reference_id, {"verified": verified})
    db.commit()
    return {"reference_id": r.reference_id, "verification_status": r.verification_status, "last_verified_date": str(r.last_verified_date)}


@admin.patch("/agents/{agent_id}")
def patch_agent(agent_id: str, body: AgentPatch, actor: User = AdminDep, db: Session = Depends(get_db)):
    a = db.get(WellnessAgent, agent_id)
    if a is None:
        raise HTTPException(404, "Not found")
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(a, k, v)
    audit(db, actor.user_id, "admin_agent_updated", None, agent_id, data)
    db.commit()
    return {"ok": True}


@admin.get("/users")
def users(_: User = AdminDep, db: Session = Depends(get_db)):
    """User management. Deliberately excludes any wellness data."""
    return [{"user_id": str(u.user_id), "full_name": u.full_name, "email": u.email, "user_role": u.user_role,
             "account_status": u.account_status, "registration_date": u.registration_date.isoformat(), "is_synthetic": u.is_synthetic}
            for u in db.scalars(select(User).where(User.account_status != "deleted").order_by(User.user_role, User.full_name))]


@admin.post("/users", status_code=201)
def create_user(body: UserCreate, actor: User = AdminDep, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == body.email.lower())):
        raise HTTPException(409, "Email exists")
    u = User(full_name=body.full_name, email=body.email.lower(), password_hash=hash_password(body.password),
             user_role=body.user_role, occupation=body.occupation)
    db.add(u)
    db.flush()
    db.add(UserPreference(user_id=u.user_id))
    audit(db, actor.user_id, "admin_user_created", u.user_id, body.user_role)
    db.commit()
    return user_out(u)


@admin.patch("/users/{user_id}")
def patch_user(user_id: uuid.UUID, body: UserPatch, actor: User = AdminDep, db: Session = Depends(get_db)):
    u = db.get(User, user_id)
    if u is None:
        raise HTTPException(404, "Not found")
    if u.user_id == actor.user_id and body.user_role and body.user_role != "admin":
        raise HTTPException(400, "You cannot remove your own admin role")
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(u, k, v)
    audit(db, actor.user_id, "admin_user_updated", u.user_id, None, data)
    db.commit()
    return user_out(u)


@admin.get("/analytics")
def analytics(group_by: str = Query("industry", pattern="^(industry|age_group|city|occupation)$"), _: User = AdminDep, db: Session = Depends(get_db)):
    """Anonymised, aggregated category averages with a minimum group size.

    Uses each person's latest assessment only. Groups smaller than the minimum
    size are suppressed so no individual can be singled out.
    """
    k = get_settings().min_group_size
    latest = (select(AssessmentSession.user_id, func.max(AssessmentSession.assessment_date).label("d"))
              .where(AssessmentSession.deleted_at.is_(None), AssessmentSession.completion_status == "completed")
              .group_by(AssessmentSession.user_id).subquery())
    col = getattr(User, group_by)
    rows = db.execute(
        select(col, WellnessCategoryScore.category_id, WellnessCategoryScore.calculated_score, User.user_id)
        .join(AssessmentSession, AssessmentSession.assessment_id == WellnessCategoryScore.assessment_id)
        .join(latest, (latest.c.user_id == AssessmentSession.user_id) & (latest.c.d == AssessmentSession.assessment_date))
        .join(User, User.user_id == AssessmentSession.user_id)
        .where(User.account_status == "active")
    ).all()
    groups: dict[str, dict] = defaultdict(lambda: {"users": set(), "scores": defaultdict(list)})
    for g, cid, score, uid in rows:
        key = g or "Not specified"
        groups[key]["users"].add(uid)
        if score is not None:
            groups[key]["scores"][cid].append(score)
    out, suppressed = [], 0
    for g, data in sorted(groups.items()):
        n = len(data["users"])
        if n < k:
            suppressed += 1
            continue
        out.append({"group": g, "people": n, "averages": {c: round(sum(v) / len(v), 1) for c, v in data["scores"].items() if len(v) >= k}})
    return {"group_by": group_by, "min_group_size": k, "groups": out, "suppressed_groups": suppressed}


@admin.get("/audit-logs")
def audit_logs(limit: int = Query(100, le=500), _: User = AdminDep, db: Session = Depends(get_db)):
    return [{"audit_id": str(a.audit_id), "actor_id": str(a.actor_id) if a.actor_id else None, "action": a.action,
             "subject_user_id": str(a.subject_user_id) if a.subject_user_id else None, "resource": a.resource,
             "created_at": a.created_at.isoformat()}
            for a in db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit))]


@admin.get("/system")
def system(_: User = AdminDep, db: Session = Depends(get_db)):
    stats = db.execute(select(AgentExecutionLog.agent_id, AgentExecutionLog.status, func.count(), func.avg(AgentExecutionLog.duration_ms))
                       .group_by(AgentExecutionLog.agent_id, AgentExecutionLog.status)).all()
    agents: dict = defaultdict(lambda: {"succeeded": 0, "failed": 0, "avg_ms": None})
    for aid, status, n, avg in stats:
        agents[aid][status] = n
        if status == "succeeded":
            agents[aid]["avg_ms"] = round(avg or 0)
    return {
        "users": db.scalar(select(func.count()).select_from(User).where(User.account_status == "active")),
        "assessments": db.scalar(select(func.count()).select_from(AssessmentSession)),
        "active_grants": db.scalar(select(func.count()).select_from(AccessGrant).where(AccessGrant.status == "active")),
        "agent_stats": agents,
    }


@admin.post("/notifications/run")
def run_reminders(_: User = AdminDep, db: Session = Depends(get_db)):
    """Reminder engine entry point — call from a scheduler (e.g. daily cron)."""
    n = 0
    for u in db.scalars(select(User).where(User.user_role == "individual", User.account_status == "active")).all():
        generate_notifications(db, u)
        n += 1
    return {"processed_users": n}
