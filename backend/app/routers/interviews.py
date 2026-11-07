"""Interview-based assessment for wellness coaches and counsellors."""
import uuid
from datetime import date, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import InterviewRecord, InterviewTranscript, User, WellnessCategory, WellnessCategoryScore
from ..security import current_user, require_roles
from ..services.access import ensure_can_view
from ..services.assessment import Answer, submit_assessment
from ..services.audit import audit
from ..services.crypto import decrypt, encrypt
from ..services.orchestrator import run_agents
from ..services.safety import CRISIS_GUIDANCE, detect_crisis
from .assessments import AnswerIn, session_out
from .privacy import has_consent

router = APIRouter(prefix="/interviews", tags=["Interviews"])


class InterviewIn(BaseModel):
    user_id: uuid.UUID
    answers: list[AnswerIn] = Field(min_length=1, max_length=200)
    category_comments: dict[str, str] = {}
    observations: dict[str, str] = {}  # interviewer's observations per category
    interview_summary: str | None = Field(default=None, max_length=5000)
    transcript: str | None = Field(default=None, max_length=100_000)
    follow_up_plan: str | None = None
    follow_up_date: date | None = None


class ScheduleIn(BaseModel):
    user_id: uuid.UUID
    scheduled_for: datetime


class UpdateIn(BaseModel):
    interview_summary: str | None = None
    follow_up_plan: str | None = None
    follow_up_date: date | None = None
    status: str | None = None


def out(iv: InterviewRecord, db: Session) -> dict:
    return {
        "interview_id": str(iv.interview_id), "user_id": str(iv.user_id), "user_name": db.get(User, iv.user_id).full_name,
        "interviewer_id": str(iv.interviewer_id), "interviewer_name": db.get(User, iv.interviewer_id).full_name,
        "assessment_id": str(iv.assessment_id) if iv.assessment_id else None,
        "interview_date": iv.interview_date.isoformat(), "scheduled_for": iv.scheduled_for.isoformat() if iv.scheduled_for else None,
        "status": iv.status, "observations": iv.observations or {}, "interview_summary": iv.interview_summary,
        "summary_source": iv.summary_source, "has_transcript": iv.transcription_reference is not None,
        "consent_status": iv.consent_status, "follow_up_plan": iv.follow_up_plan,
        "follow_up_date": iv.follow_up_date.isoformat() if iv.follow_up_date else None,
    }


@router.post("", status_code=201)
def conduct_interview(body: InterviewIn, bg: BackgroundTasks, actor: User = Depends(require_roles("coach", "counselor")), db: Session = Depends(get_db)):
    ensure_can_view(db, actor, body.user_id, "interviews")
    consent_status = "not_requested"
    transcript_id = None
    if body.transcript:
        if not has_consent(db, body.user_id, "interview_transcription"):
            raise HTTPException(403, "The individual has not consented to interview transcription. Save without a transcript.")
        consent_status = "granted"
        t = InterviewTranscript(owner_user_id=body.user_id, ciphertext=encrypt(body.transcript))
        db.add(t)
        db.flush()
        transcript_id = t.transcript_id
    answers = [Answer(a.parameter_id, a.value, a.status, a.comment) for a in body.answers]
    session, crisis = submit_assessment(db, body.user_id, answers, body.category_comments, source="interview", interviewer_id=actor.user_id)
    iv = InterviewRecord(
        user_id=body.user_id, interviewer_id=actor.user_id, assessment_id=session.assessment_id,
        observations=body.observations, interview_summary=body.interview_summary,
        summary_source="interviewer" if body.interview_summary else None,
        transcription_reference=transcript_id, consent_status=consent_status,
        follow_up_plan=body.follow_up_plan, follow_up_date=body.follow_up_date,
    )
    db.add(iv)
    audit(db, actor.user_id, "interview_recorded", body.user_id, str(session.assessment_id))
    db.commit()
    bg.add_task(run_agents, session.assessment_id)
    crisis = crisis or detect_crisis(*body.observations.values(), body.transcript)
    return {"interview": out(iv, db), "assessment": session_out(db, session), "safety": CRISIS_GUIDANCE if crisis else None}


@router.post("/schedule", status_code=201)
def schedule(body: ScheduleIn, actor: User = Depends(require_roles("coach", "counselor")), db: Session = Depends(get_db)):
    ensure_can_view(db, actor, body.user_id, "interviews")
    iv = InterviewRecord(user_id=body.user_id, interviewer_id=actor.user_id, interview_date=body.scheduled_for,
                         scheduled_for=body.scheduled_for, status="scheduled")
    db.add(iv)
    db.commit()
    return out(iv, db)


@router.get("")
def list_interviews(user_id: uuid.UUID | None = Query(None), actor: User = Depends(current_user), db: Session = Depends(get_db)):
    q = select(InterviewRecord).order_by(InterviewRecord.interview_date.desc())
    if actor.user_role == "individual":
        q = q.where(InterviewRecord.user_id == actor.user_id)
    elif actor.user_role in ("coach", "counselor"):
        q = q.where(InterviewRecord.interviewer_id == actor.user_id)
        if user_id:
            ensure_can_view(db, actor, user_id, "interviews")
            q = q.where(InterviewRecord.user_id == user_id)
    else:
        raise HTTPException(403, "Administrators cannot view individual interviews")
    rows = db.scalars(q).all()
    if actor.user_role in ("coach", "counselor"):
        # only show records for individuals who still grant access
        from ..services.access import active_grant
        rows = [r for r in rows if active_grant(db, r.user_id, actor.user_id, "interviews")]
    db.commit()
    return [out(r, db) for r in rows]


def _get(db, interview_id, actor) -> InterviewRecord:
    iv = db.get(InterviewRecord, interview_id)
    if iv is None:
        raise HTTPException(404, "Interview not found")
    if actor.user_id not in (iv.user_id, iv.interviewer_id):
        raise HTTPException(403, "Not your interview")
    if actor.user_id == iv.interviewer_id:
        ensure_can_view(db, actor, iv.user_id, "interviews")
    return iv


@router.patch("/{interview_id}")
def update(interview_id: uuid.UUID, body: UpdateIn, actor: User = Depends(require_roles("coach", "counselor")), db: Session = Depends(get_db)):
    iv = _get(db, interview_id, actor)
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(iv, k, v)
    if "interview_summary" in data:
        iv.summary_source = "interviewer"  # reviewed/edited by a human
    db.commit()
    return out(iv, db)


@router.post("/{interview_id}/ai-summary")
def draft_summary(interview_id: uuid.UUID, actor: User = Depends(require_roles("coach", "counselor")), db: Session = Depends(get_db)):
    """Draft a summary from recorded scores and observations.

    The draft is returned for the interviewer to review; it is NOT saved and it
    never modifies the individual's answers or scores.
    """
    iv = _get(db, interview_id, actor)
    if iv.assessment_id is None:
        raise HTTPException(400, "Interview has no linked assessment")
    names = {c.category_id: c.category_name for c in db.scalars(select(WellnessCategory))}
    scores = db.scalars(select(WellnessCategoryScore).where(WellnessCategoryScore.assessment_id == iv.assessment_id)).all()
    scored = sorted([s for s in scores if s.calculated_score is not None], key=lambda s: s.calculated_score)
    low = [f"{names[s.category_id]} ({s.calculated_score:.0f})" for s in scored[:3]]
    high = [f"{names[s.category_id]} ({s.calculated_score:.0f})" for s in scored[-3:][::-1]]
    obs = [f"{names.get(k, k)}: {v}" for k, v in (iv.observations or {}).items() if v]
    text = (f"Interview on {iv.interview_date.date().isoformat()}. Relative strengths: {', '.join(high) or '—'}. "
            f"Areas to explore: {', '.join(low) or '—'}." + (f" Interviewer observations — {'; '.join(obs)}." if obs else "")
            + " (Draft generated from recorded data; please review before saving.)")
    return {"draft": text, "label": "AI-assisted draft — not saved until you edit and confirm"}


@router.get("/{interview_id}/transcript")
def transcript(interview_id: uuid.UUID, actor: User = Depends(current_user), db: Session = Depends(get_db)):
    iv = _get(db, interview_id, actor)
    if iv.transcription_reference is None:
        raise HTTPException(404, "No transcript")
    t = db.get(InterviewTranscript, iv.transcription_reference)
    audit(db, actor.user_id, "transcript_viewed", iv.user_id, str(iv.interview_id))
    db.commit()
    return {"transcript": decrypt(t.ciphertext)}
