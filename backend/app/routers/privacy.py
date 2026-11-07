"""Profile, preferences, consent, access grants and data-subject rights (DPDP Act)."""
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    AccessGrant,
    AssessmentResponse,
    AssessmentSession,
    ConsentRecord,
    HabitLog,
    MicroHabit,
    QuarterlyReview,
    User,
    UserPreference,
    WellnessCategoryScore,
)
from ..security import current_user, require_roles
from ..seed.seed import CONSENT_VERSION
from ..services.access import SCOPES
from ..services.audit import audit
from .auth import user_out

router = APIRouter(tags=["Profile & Privacy"])

CONSENT_TYPES = ("data_processing", "ai_analysis", "interview_transcription", "push_notifications", "anonymized_research")


class ProfileIn(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    phone_number: str | None = None
    occupation: str | None = None
    industry: str | None = None
    age_group: str | None = None
    city: str | None = None


class PrefIn(BaseModel):
    theme: str | None = None
    language: str | None = None
    reminders_enabled: bool | None = None
    push_enabled: bool | None = None


class ConsentIn(BaseModel):
    consent_type: str
    granted: bool


class GrantIn(BaseModel):
    grantee_id: uuid.UUID
    scopes: list[str]
    expires_in_days: int | None = Field(default=None, ge=1, le=730)


@router.get("/me/profile")
def get_profile(user: User = Depends(current_user)):
    return user_out(user)


@router.put("/me/profile")
def update_profile(body: ProfileIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(user, k, v)
    db.add(user)
    audit(db, user.user_id, "profile_corrected", user.user_id)
    db.commit()
    return user_out(user)


@router.get("/me/preferences")
def get_prefs(user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = db.scalar(select(UserPreference).where(UserPreference.user_id == user.user_id))
    if p is None:
        p = UserPreference(user_id=user.user_id)
        db.add(p)
        db.commit()
    return {"theme": p.theme, "language": p.language, "reminders_enabled": p.reminders_enabled, "push_enabled": p.push_enabled}


@router.put("/me/preferences")
def set_prefs(body: PrefIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = db.scalar(select(UserPreference).where(UserPreference.user_id == user.user_id)) or UserPreference(user_id=user.user_id)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    db.add(p)
    db.commit()
    return get_prefs(user, db)


def _latest_consents(db: Session, user_id) -> dict:
    rows = db.scalars(select(ConsentRecord).where(ConsentRecord.user_id == user_id).order_by(ConsentRecord.consent_timestamp)).all()
    latest = {}
    for r in rows:
        latest[r.consent_type] = r
    return {
        t: {
            "granted": bool(latest[t].granted_status and latest[t].withdrawal_timestamp is None) if t in latest else False,
            "version": latest[t].consent_version if t in latest else None,
            "timestamp": latest[t].consent_timestamp.isoformat() if t in latest else None,
        }
        for t in CONSENT_TYPES
    }


def has_consent(db: Session, user_id, consent_type: str) -> bool:
    return _latest_consents(db, user_id)[consent_type]["granted"]


@router.get("/consents")
def list_consents(user: User = Depends(current_user), db: Session = Depends(get_db)):
    history = db.scalars(select(ConsentRecord).where(ConsentRecord.user_id == user.user_id).order_by(ConsentRecord.consent_timestamp.desc())).all()
    return {
        "current": _latest_consents(db, user.user_id),
        "history": [{"type": h.consent_type, "granted": h.granted_status, "version": h.consent_version,
                     "timestamp": h.consent_timestamp.isoformat(),
                     "withdrawn": h.withdrawal_timestamp.isoformat() if h.withdrawal_timestamp else None} for h in history],
    }


@router.post("/consents")
def set_consent(body: ConsentIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if body.consent_type not in CONSENT_TYPES:
        raise HTTPException(422, "Unknown consent type")
    now = datetime.now(timezone.utc)
    if not body.granted:
        for r in db.scalars(select(ConsentRecord).where(ConsentRecord.user_id == user.user_id, ConsentRecord.consent_type == body.consent_type,
                                                        ConsentRecord.withdrawal_timestamp.is_(None), ConsentRecord.granted_status)):
            r.withdrawal_timestamp = now
    db.add(ConsentRecord(user_id=user.user_id, consent_type=body.consent_type, consent_version=CONSENT_VERSION, granted_status=body.granted))
    audit(db, user.user_id, "consent_" + ("granted" if body.granted else "withdrawn"), user.user_id, body.consent_type)
    db.commit()
    return _latest_consents(db, user.user_id)


# ------------------------------------------------------------- access grants
@router.get("/professionals")
def list_professionals(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(User).where(User.user_role.in_(["coach", "counselor"]), User.account_status == "active").order_by(User.full_name))
    return [{"user_id": str(u.user_id), "full_name": u.full_name, "user_role": u.user_role, "occupation": u.occupation} for u in rows]


def _grant_out(db, g: AccessGrant) -> dict:
    grantee = db.get(User, g.grantee_id)
    owner = db.get(User, g.user_id)
    return {"grant_id": str(g.grant_id), "user_id": str(g.user_id), "user_name": owner.full_name,
            "grantee_id": str(g.grantee_id), "grantee_name": grantee.full_name, "grantee_role": grantee.user_role,
            "scopes": g.scopes, "status": g.status, "granted_at": g.granted_at.isoformat(),
            "expires_at": g.expires_at.isoformat() if g.expires_at else None,
            "revoked_at": g.revoked_at.isoformat() if g.revoked_at else None}


@router.get("/access-grants")
def my_grants(user: User = Depends(current_user), db: Session = Depends(get_db)):
    col = AccessGrant.grantee_id if user.user_role in ("coach", "counselor") else AccessGrant.user_id
    return [_grant_out(db, g) for g in db.scalars(select(AccessGrant).where(col == user.user_id).order_by(AccessGrant.granted_at.desc()))]


@router.post("/access-grants", status_code=201)
def create_grant(body: GrantIn, user: User = Depends(require_roles("individual")), db: Session = Depends(get_db)):
    grantee = db.get(User, body.grantee_id)
    if grantee is None or grantee.user_role not in ("coach", "counselor"):
        raise HTTPException(404, "Coach or counsellor not found")
    bad = [s for s in body.scopes if s not in SCOPES]
    if bad or not body.scopes:
        raise HTTPException(422, f"Invalid scopes {bad}")
    if "observations" in body.scopes and grantee.user_role != "counselor":
        raise HTTPException(422, "Only counsellors can be granted the observations scope")
    for g in db.scalars(select(AccessGrant).where(AccessGrant.user_id == user.user_id, AccessGrant.grantee_id == grantee.user_id, AccessGrant.status == "active")):
        g.status, g.revoked_at = "revoked", datetime.now(timezone.utc)
    g = AccessGrant(user_id=user.user_id, grantee_id=grantee.user_id, scopes=body.scopes,
                    expires_at=datetime.now(timezone.utc) + timedelta(days=body.expires_in_days) if body.expires_in_days else None)
    db.add(g)
    audit(db, user.user_id, "access_granted", user.user_id, str(grantee.user_id), {"scopes": body.scopes})
    db.commit()
    return _grant_out(db, g)


@router.delete("/access-grants/{grant_id}")
def revoke_grant(grant_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    g = db.get(AccessGrant, grant_id)
    if g is None or g.user_id != user.user_id:
        raise HTTPException(404, "Grant not found")
    g.status, g.revoked_at = "revoked", datetime.now(timezone.utc)
    audit(db, user.user_id, "access_revoked", user.user_id, str(g.grantee_id))
    db.commit()
    return _grant_out(db, g)


# ------------------------------------------------------------- data rights
@router.get("/me/export")
def export_my_data(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Right to access: a machine-readable copy of the person's data."""
    sessions = db.scalars(select(AssessmentSession).where(AssessmentSession.user_id == user.user_id, AssessmentSession.deleted_at.is_(None))).all()
    out = {"profile": user_out(user), "consents": list_consents(user, db), "assessments": []}
    for s in sessions:
        out["assessments"].append({
            "assessment_id": str(s.assessment_id), "date": s.assessment_date.isoformat(), "period": s.assessment_period,
            "source": s.assessment_source, "overall_indicator": s.overall_indicator,
            "responses": [{"parameter_id": r.parameter_id, "value": r.response_value, "status": r.response_status}
                          for r in db.scalars(select(AssessmentResponse).where(AssessmentResponse.assessment_id == s.assessment_id))],
            "scores": [{"category_id": c.category_id, "score": c.calculated_score, "level": c.wellness_level}
                       for c in db.scalars(select(WellnessCategoryScore).where(WellnessCategoryScore.assessment_id == s.assessment_id))],
        })
    out["habits"] = [{"habit": h.habit_name, "category_id": h.category_id, "frequency": h.frequency, "completions": h.completion_count}
                     for h in db.scalars(select(MicroHabit).where(MicroHabit.user_id == user.user_id))]
    out["reviews"] = [{"quarter": f"{r.year}-Q{r.quarter}", "summary": r.review_summary}
                      for r in db.scalars(select(QuarterlyReview).where(QuarterlyReview.user_id == user.user_id))]
    audit(db, user.user_id, "data_exported", user.user_id)
    db.commit()
    return out


@router.delete("/me")
def delete_account(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Right to erasure: soft-delete assessments, revoke grants, anonymise identity.

    Rows are retained in de-identified form only where referential integrity of
    shared records (e.g. a coach's interview log) requires it.
    """
    now = datetime.now(timezone.utc)
    for s in db.scalars(select(AssessmentSession).where(AssessmentSession.user_id == user.user_id)):
        s.deleted_at = now
    for g in db.scalars(select(AccessGrant).where(AccessGrant.user_id == user.user_id)):
        g.status, g.revoked_at = "revoked", now
    for h in db.scalars(select(MicroHabit).where(MicroHabit.user_id == user.user_id)):
        db.query(HabitLog).filter(HabitLog.habit_id == h.habit_id).delete()
        db.delete(h)
    audit(db, user.user_id, "account_deleted", user.user_id)
    user.full_name = "Deleted user"
    user.email = f"deleted-{user.user_id}@deleted.invalid"
    user.phone_number = user.city = user.occupation = None
    user.password_hash = "!"
    user.account_status = "deleted"
    user.deleted_at = now
    db.commit()
    return {"status": "deleted"}
