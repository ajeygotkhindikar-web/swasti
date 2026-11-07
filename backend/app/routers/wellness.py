import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    HabitLog,
    MicroHabit,
    Notification,
    QuarterlyReview,
    ScientificReference,
    User,
    UserWellnessPlan,
    WellnessCategory,
    WellnessRecommendation,
)
from ..security import current_user, require_roles
from ..services.access import active_grant, resolve_subject
from ..services.audit import audit
from ..services.dashboard import build_dashboard
from ..services.reports import build_pdf
from ..services.reviews import create_review, generate_notifications

router = APIRouter(tags=["Wellness"])


# ------------------------------------------------------------- dashboard
@router.get("/dashboard")
def dashboard(user_id: uuid.UUID | None = Query(None), user: User = Depends(current_user), db: Session = Depends(get_db)):
    if user.user_role == "admin" and user_id is None:
        raise HTTPException(403, "Administrators see anonymised analytics only (Administration → Analytics).")
    subject = resolve_subject(db, user, user_id, "assessments")
    db.commit()
    return build_dashboard(db, subject)


# ------------------------------------------------------------- knowledge base
def rec_out(r: WellnessRecommendation, ref: ScientificReference | None) -> dict:
    return {
        "recommendation_id": r.recommendation_id, "category_id": r.category_id, "agent_id": r.agent_id,
        "title": r.recommendation_title, "description": r.recommendation_description, "action": r.recommended_action,
        "micro_habit": r.micro_habit, "frequency": r.suggested_frequency, "priority": r.recommendation_priority,
        "target_parameters": r.target_parameters,
        "evidence": None if ref is None else {
            "reference_id": ref.reference_id, "title": ref.reference_title, "organization": ref.issuing_organization,
            "url": ref.reference_url, "publication_date": ref.publication_date, "evidence_level": ref.evidence_level,
            "supporting_evidence": ref.supporting_evidence, "verification_status": ref.verification_status,
            "last_verified_date": ref.last_verified_date.isoformat() if ref.last_verified_date else None,
        },
    }


@router.get("/recommendations")
def knowledge_base(category_id: str | None = None, db: Session = Depends(get_db), _: User = Depends(current_user)):
    q = select(WellnessRecommendation, ScientificReference).join(
        ScientificReference, ScientificReference.reference_id == WellnessRecommendation.evidence_reference
    ).where(WellnessRecommendation.is_active)
    if category_id:
        q = q.where(WellnessRecommendation.category_id == category_id)
    return [rec_out(r, ref) for r, ref in db.execute(q.order_by(WellnessRecommendation.recommendation_id))]


@router.get("/references")
def references(db: Session = Depends(get_db), _: User = Depends(current_user)):
    return [
        {"reference_id": r.reference_id, "category_id": r.category_id, "title": r.reference_title, "organization": r.issuing_organization,
         "url": r.reference_url, "publication_date": r.publication_date, "evidence_level": r.evidence_level,
         "supporting_evidence": r.supporting_evidence, "verification_status": r.verification_status,
         "last_verified_date": r.last_verified_date.isoformat() if r.last_verified_date else None}
        for r in db.scalars(select(ScientificReference).order_by(ScientificReference.reference_id))
    ]


# ------------------------------------------------------------- wellness plans
class PlanIn(BaseModel):
    recommendation_id: str
    target_date: date | None = None
    create_habit: bool = True


class PlanUpdate(BaseModel):
    completion_status: str | None = Field(default=None, pattern="^(active|completed|dropped)$")
    user_feedback: str | None = Field(default=None, max_length=2000)


def plan_out(p: UserWellnessPlan, r: WellnessRecommendation) -> dict:
    return {"plan_id": str(p.plan_id), "recommendation_id": p.recommendation_id, "category_id": p.category_id,
            "title": r.recommendation_title, "action": r.recommended_action, "micro_habit": r.micro_habit,
            "start_date": p.start_date.isoformat(), "target_date": p.target_date.isoformat() if p.target_date else None,
            "completion_status": p.completion_status, "user_feedback": p.user_feedback}


@router.get("/plans")
def plans(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.execute(select(UserWellnessPlan, WellnessRecommendation).join(
        WellnessRecommendation, WellnessRecommendation.recommendation_id == UserWellnessPlan.recommendation_id
    ).where(UserWellnessPlan.user_id == user.user_id).order_by(UserWellnessPlan.created_at.desc()))
    return [plan_out(p, r) for p, r in rows]


@router.post("/plans", status_code=201)
def add_plan(body: PlanIn, user: User = Depends(require_roles("individual")), db: Session = Depends(get_db)):
    r = db.get(WellnessRecommendation, body.recommendation_id)
    if r is None:
        raise HTTPException(404, "Recommendation not found")
    existing = db.scalar(select(UserWellnessPlan).where(UserWellnessPlan.user_id == user.user_id, UserWellnessPlan.recommendation_id == r.recommendation_id))
    if existing:
        existing.completion_status = "active"
        db.commit()
        return plan_out(existing, r)
    p = UserWellnessPlan(user_id=user.user_id, category_id=r.category_id, recommendation_id=r.recommendation_id,
                         target_date=body.target_date or date.today() + timedelta(days=90))
    db.add(p)
    if body.create_habit and not db.scalar(select(MicroHabit).where(MicroHabit.user_id == user.user_id, MicroHabit.recommendation_id == r.recommendation_id, MicroHabit.status != "archived")):
        db.add(MicroHabit(user_id=user.user_id, category_id=r.category_id, recommendation_id=r.recommendation_id,
                          habit_name=r.micro_habit, frequency=r.suggested_frequency, target_frequency=1))
    db.commit()
    return plan_out(p, r)


@router.patch("/plans/{plan_id}")
def update_plan(plan_id: uuid.UUID, body: PlanUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = db.get(UserWellnessPlan, plan_id)
    if p is None or p.user_id != user.user_id:
        raise HTTPException(404, "Plan not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    db.commit()
    return plan_out(p, db.get(WellnessRecommendation, p.recommendation_id))


# ------------------------------------------------------------- micro-habits
class HabitIn(BaseModel):
    category_id: str
    habit_name: str = Field(min_length=2, max_length=200)
    frequency: str = Field(pattern="^(daily|weekly)$")
    target_frequency: int = Field(default=1, ge=1, le=14)
    reminder_time: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    recommendation_id: str | None = None


class HabitUpdate(BaseModel):
    habit_name: str | None = Field(default=None, min_length=2, max_length=200)
    frequency: str | None = Field(default=None, pattern="^(daily|weekly)$")
    target_frequency: int | None = Field(default=None, ge=1, le=14)
    reminder_time: str | None = None
    status: str | None = Field(default=None, pattern="^(active|paused|archived)$")
    user_feedback: str | None = Field(default=None, max_length=2000)


class LogIn(BaseModel):
    log_date: date | None = None
    note: str | None = Field(default=None, max_length=500)


def habit_out(db: Session, h: MicroHabit) -> dict:
    today = date.today()
    logs = {l.log_date for l in db.scalars(select(HabitLog).where(HabitLog.habit_id == h.habit_id, HabitLog.log_date >= today - timedelta(days=27)))}
    week_start = today - timedelta(days=today.weekday())
    this_period = sum(1 for d in logs if d == today) if h.frequency == "daily" else sum(1 for d in logs if d >= week_start)
    return {
        "habit_id": str(h.habit_id), "category_id": h.category_id, "habit_name": h.habit_name, "frequency": h.frequency,
        "target_frequency": h.target_frequency, "completion_count": h.completion_count, "reminder_time": h.reminder_time,
        "start_date": h.start_date.isoformat(), "status": h.status, "user_feedback": h.user_feedback,
        "recommendation_id": h.recommendation_id, "done_today": today in logs, "this_period": this_period,
        "last_28_days": [(today - timedelta(days=i)).isoformat() in {d.isoformat() for d in logs} for i in range(27, -1, -1)],
    }


def _habit(db, habit_id, user) -> MicroHabit:
    h = db.get(MicroHabit, habit_id)
    if h is None or h.user_id != user.user_id:
        raise HTTPException(404, "Habit not found")
    return h


@router.get("/habits")
def list_habits(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(MicroHabit).where(MicroHabit.user_id == user.user_id, MicroHabit.status != "archived").order_by(MicroHabit.created_at))
    return [habit_out(db, h) for h in rows]


@router.post("/habits", status_code=201)
def create_habit(body: HabitIn, user: User = Depends(require_roles("individual")), db: Session = Depends(get_db)):
    if db.get(WellnessCategory, body.category_id) is None:
        raise HTTPException(422, "Unknown category")
    h = MicroHabit(user_id=user.user_id, **body.model_dump())
    db.add(h)
    db.commit()
    return habit_out(db, h)


@router.patch("/habits/{habit_id}")
def update_habit(habit_id: uuid.UUID, body: HabitUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    h = _habit(db, habit_id, user)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(h, k, v)
    db.commit()
    return habit_out(db, h)


@router.post("/habits/{habit_id}/log")
def log_habit(habit_id: uuid.UUID, body: LogIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    h = _habit(db, habit_id, user)
    d = body.log_date or date.today()
    if d > date.today():
        raise HTTPException(422, "Cannot log a future date")
    db.add(HabitLog(habit_id=h.habit_id, log_date=d, note=body.note))
    try:
        h.completion_count += 1
        db.commit()
    except IntegrityError:
        db.rollback()  # already logged that day — idempotent
    return habit_out(db, db.get(MicroHabit, habit_id))


@router.delete("/habits/{habit_id}/log")
def unlog_habit(habit_id: uuid.UUID, log_date: date | None = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    h = _habit(db, habit_id, user)
    row = db.scalar(select(HabitLog).where(HabitLog.habit_id == h.habit_id, HabitLog.log_date == (log_date or date.today())))
    if row:
        db.delete(row)
        h.completion_count = max(0, h.completion_count - 1)
        db.commit()
    return habit_out(db, h)


# ------------------------------------------------------------- quarterly reviews
def review_out(r: QuarterlyReview, db: Session) -> dict:
    coach = db.get(User, r.coach_id) if r.coach_id else None
    return {"review_id": str(r.review_id), "user_id": str(r.user_id), "quarter": r.quarter, "year": r.year,
            "previous_assessment_id": str(r.previous_assessment_id) if r.previous_assessment_id else None,
            "current_assessment_id": str(r.current_assessment_id), "overall_progress": r.overall_progress,
            "comparison": r.comparison, "review_summary": r.review_summary, "coach_name": coach.full_name if coach else None,
            "coach_notes": r.coach_notes, "review_date": r.review_date.isoformat()}


@router.get("/reviews")
def list_reviews(user_id: uuid.UUID | None = Query(None), user: User = Depends(current_user), db: Session = Depends(get_db)):
    subject = resolve_subject(db, user, user_id, "assessments")
    db.commit()
    return [review_out(r, db) for r in db.scalars(select(QuarterlyReview).where(QuarterlyReview.user_id == subject).order_by(QuarterlyReview.review_date.desc(), QuarterlyReview.created_at.desc()))]


@router.post("/reviews", status_code=201)
def new_review(user_id: uuid.UUID | None = Query(None), user: User = Depends(current_user), db: Session = Depends(get_db)):
    subject = resolve_subject(db, user, user_id, "assessments")
    r = create_review(db, subject, coach_id=user.user_id if user.user_role in ("coach", "counselor") else None)
    return review_out(r, db)


class CoachNotes(BaseModel):
    coach_notes: str = Field(max_length=5000)


@router.patch("/reviews/{review_id}/coach-notes")
def coach_notes(review_id: uuid.UUID, body: CoachNotes, user: User = Depends(require_roles("coach", "counselor")), db: Session = Depends(get_db)):
    r = db.get(QuarterlyReview, review_id)
    if r is None or not active_grant(db, r.user_id, user.user_id, "assessments"):
        raise HTTPException(404, "Review not found")
    r.coach_notes, r.coach_id = body.coach_notes, user.user_id
    db.commit()
    return review_out(r, db)


# ------------------------------------------------------------- reports
@router.get("/reports/pdf")
def report_pdf(user_id: uuid.UUID | None = Query(None), kind: str = Query("individual", pattern="^(individual|coach)$"),
               user: User = Depends(current_user), db: Session = Depends(get_db)):
    subject_id = resolve_subject(db, user, user_id, "reports")
    if kind == "coach" and user.user_role not in ("coach", "counselor"):
        kind = "individual"
    subject = db.get(User, subject_id)
    audit(db, user.user_id, "report_generated", subject_id, kind)
    db.commit()
    pdf = build_pdf(db, subject, kind, viewer=user)
    fname = f"swasti-{kind}-report-{date.today().isoformat()}.pdf"
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{fname}"'})


# ------------------------------------------------------------- notifications
@router.get("/notifications")
def notifications(user: User = Depends(current_user), db: Session = Depends(get_db)):
    generate_notifications(db, user)
    rows = db.scalars(select(Notification).where(Notification.user_id == user.user_id).order_by(Notification.created_at.desc()).limit(30))
    return [{"notification_id": str(n.notification_id), "type": n.notification_type, "title": n.title, "message": n.message,
             "is_read": n.is_read, "created_at": n.created_at.isoformat()} for n in rows]


@router.post("/notifications/{notification_id}/read")
def mark_read(notification_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    n = db.get(Notification, notification_id)
    if n is None or n.user_id != user.user_id:
        raise HTTPException(404, "Not found")
    n.is_read = True
    db.commit()
    return {"ok": True}
