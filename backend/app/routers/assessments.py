import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    AgentAssessment,
    AgentExecutionLog,
    AssessmentResponse,
    AssessmentSession,
    CategoryComment,
    User,
    WellnessAgent,
    WellnessCategory,
    WellnessCategoryScore,
)
from ..security import current_user
from ..services.access import ensure_can_view, resolve_subject
from ..services.agents import get_agent
from ..services.assessment import Answer, submit_assessment
from ..services.orchestrator import build_cross_insights, run_agents
from ..services.safety import CRISIS_GUIDANCE

router = APIRouter(tags=["Assessments & Agents"])


@router.get("/categories")
def categories(db: Session = Depends(get_db), _: User = Depends(current_user)):
    cats = db.scalars(select(WellnessCategory).where(WellnessCategory.is_active).order_by(WellnessCategory.display_order))
    return [
        {
            "category_id": c.category_id, "category_name": c.category_name, "description": c.category_description,
            "icon": c.category_icon, "weightage": c.default_weightage, "target_score": c.target_score, "agent_code": c.agent_code,
            "parameters": [
                {"parameter_id": p.parameter_id, "name": p.parameter_name, "question": p.parameter_description,
                 "response_type": p.response_type, "options": p.options, "reverse": p.scoring_rule.get("reverse", False),
                 "weightage": p.parameter_weightage, "allow_not_applicable": p.allow_not_applicable}
                for p in c.parameters if p.is_active
            ],
        }
        for c in cats
    ]


class AnswerIn(BaseModel):
    parameter_id: str
    value: int | None = Field(default=None, ge=1, le=5)
    status: str = "answered"
    comment: str | None = Field(default=None, max_length=1000)


class AssessmentIn(BaseModel):
    answers: list[AnswerIn] = Field(min_length=1, max_length=200)
    category_comments: dict[str, str] = {}


def session_out(db: Session, s: AssessmentSession, detail: bool = False) -> dict:
    scores = db.scalars(select(WellnessCategoryScore).where(WellnessCategoryScore.assessment_id == s.assessment_id)).all()
    out = {
        "assessment_id": str(s.assessment_id), "user_id": str(s.user_id), "assessment_type": s.assessment_type,
        "assessment_date": s.assessment_date.isoformat(), "assessment_period": s.assessment_period,
        "assessment_source": s.assessment_source, "interviewer_id": str(s.interviewer_id) if s.interviewer_id else None,
        "completion_status": s.completion_status, "overall_indicator": s.overall_indicator, "coverage": s.coverage,
        "agents_status": s.agents_status,
        "scores": [{"category_id": c.category_id, "score": c.calculated_score, "level": c.wellness_level,
                    "target": c.target_score, "gap": c.score_gap, "coverage": c.coverage} for c in scores],
    }
    if detail:
        out["responses"] = [
            {"parameter_id": r.parameter_id, "value": r.response_value, "status": r.response_status,
             "normalized_score": r.normalized_score, "comment": r.comments}
            for r in db.scalars(select(AssessmentResponse).where(AssessmentResponse.assessment_id == s.assessment_id))
        ]
        out["category_comments"] = {
            c.category_id: c.comment for c in db.scalars(select(CategoryComment).where(CategoryComment.assessment_id == s.assessment_id))
        }
    return out


@router.post("/assessments", status_code=201)
def create_assessment(body: AssessmentIn, bg: BackgroundTasks, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if user.user_role != "individual":
        raise HTTPException(403, "Self-assessments are completed by individuals. Use Interview Assessment for clients.")
    answers = [Answer(a.parameter_id, a.value, a.status, a.comment) for a in body.answers]
    session, crisis = submit_assessment(db, user.user_id, answers, body.category_comments, source="self")
    bg.add_task(run_agents, session.assessment_id)
    out = session_out(db, session)
    out["safety"] = CRISIS_GUIDANCE if crisis else None
    return out


def _session_or_404(db, assessment_id) -> AssessmentSession:
    s = db.get(AssessmentSession, assessment_id)
    if s is None or s.deleted_at is not None:
        raise HTTPException(404, "Assessment not found")
    return s


@router.get("/assessments")
def list_assessments(user_id: uuid.UUID | None = Query(None), user: User = Depends(current_user), db: Session = Depends(get_db)):
    subject = resolve_subject(db, user, user_id, "assessments")
    db.commit()
    rows = db.scalars(select(AssessmentSession).where(AssessmentSession.user_id == subject, AssessmentSession.deleted_at.is_(None))
                      .order_by(AssessmentSession.assessment_date.desc()))
    return [session_out(db, s) for s in rows]


@router.get("/assessments/{assessment_id}")
def get_assessment(assessment_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    s = _session_or_404(db, assessment_id)
    ensure_can_view(db, user, s.user_id, "assessments")
    db.commit()
    return session_out(db, s, detail=True)


@router.get("/assessments/{assessment_id}/agents")
def agent_results(assessment_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    s = _session_or_404(db, assessment_id)
    ensure_can_view(db, user, s.user_id, "assessments")
    db.commit()
    rows = db.scalars(select(AgentAssessment).where(AgentAssessment.assessment_id == assessment_id).order_by(AgentAssessment.execution_timestamp)).all()
    latest: dict[str, AgentAssessment] = {}
    for r in rows:
        latest[r.agent_id] = r
    return {"agents_status": s.agents_status,
            "results": [r.output | {"execution_status": r.execution_status, "executed_at": r.execution_timestamp.isoformat()} for r in latest.values()]}


@router.get("/assessments/{assessment_id}/agent-logs")
def agent_logs(assessment_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    s = _session_or_404(db, assessment_id)
    ensure_can_view(db, user, s.user_id, "assessments")
    db.commit()
    rows = db.scalars(select(AgentExecutionLog).where(AgentExecutionLog.assessment_id == assessment_id).order_by(AgentExecutionLog.started_at.desc()).limit(200))
    return [{"run_id": str(r.run_id), "agent_id": r.agent_id, "attempt": r.attempt, "status": r.status,
             "error": r.error_message, "duration_ms": r.duration_ms, "started_at": r.started_at.isoformat()} for r in rows]


class RunIn(BaseModel):
    agents: list[str] | None = None  # agent ids or category ids; None = all 14
    parallel: bool = True
    background: bool = True


@router.post("/assessments/{assessment_id}/agents/run", status_code=202)
def run(assessment_id: uuid.UUID, body: RunIn, bg: BackgroundTasks, user: User = Depends(current_user), db: Session = Depends(get_db)):
    s = _session_or_404(db, assessment_id)
    ensure_can_view(db, user, s.user_id, "assessments")
    db.commit()
    if body.background:
        bg.add_task(run_agents, assessment_id, body.agents, body.parallel)
        return {"status": "queued"}
    return run_agents(assessment_id, body.agents, body.parallel)


# ------------------------------------------------------------- agent registry
@router.get("/agents")
def list_agents(db: Session = Depends(get_db), _: User = Depends(current_user)):
    rows = db.scalars(select(WellnessAgent).order_by(WellnessAgent.agent_id))
    return [{"agent_id": a.agent_id, "category_id": a.category_id, "agent_name": a.agent_name, "description": a.agent_description,
             "version": a.agent_version, "execution_mode": a.execution_mode, "status": a.status,
             "guardrail": get_agent(a.agent_id).guardrail} for a in rows]


@router.post("/agents/{agent_id}/run")
def run_single_agent(agent_id: str, assessment_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Execute one agent independently and synchronously."""
    s = _session_or_404(db, assessment_id)
    ensure_can_view(db, user, s.user_id, "assessments")
    try:
        agent = get_agent(agent_id)
    except KeyError:
        raise HTTPException(404, "Unknown agent")
    a = db.get(WellnessAgent, agent.agent_id)
    if a is None or a.status != "active":
        raise HTTPException(409, "Agent is disabled")
    output = agent.run(db, assessment_id)
    build_cross_insights(db, assessment_id)
    db.commit()
    return output
