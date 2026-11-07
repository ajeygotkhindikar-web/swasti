"""Central Wellness Orchestrator.

Runs the 14 category agents independently (in parallel threads, each with its
own DB session), retries failures with exponential backoff, logs every
attempt, then derives cross-wellness insights from the stored results.

Cross-insights only describe co-occurring patterns in the person's own data
("these may be connected"), never causation. They don't change any score,
so the same issue is never counted twice. Each pair is reported at most once,
and each category appears in at most two insights.
"""
from __future__ import annotations

import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import SessionLocal
from ..models import (
    AgentExecutionLog,
    AssessmentSession,
    CrossWellnessInsight,
    WellnessAgent,
    WellnessCategory,
    WellnessCategoryScore,
)
from .agents import get_agent

log = logging.getLogger("sampurna.orchestrator")

# (cat_a, cat_b, observation, suggestion)
RELATIONS = [
    ("FIN", "MEN", "financial pressure and mental strain", "Breaking a money worry into one small, concrete step (such as a simple budget) can also ease mental load."),
    ("PHY", "MEN", "physical activity/sleep and mental freshness", "A short daily walk or a consistent wind-down routine can support both."),
    ("SOC", "PSY", "social connection and psychological well-being", "Sharing a setback with someone you trust can help on both fronts."),
    ("MEN", "FAM", "work-life balance and family time", "Protecting a fixed end-of-work time can create space for family."),
    ("SOC", "SPO", "physical activity and social interaction", "Consider including a group walking activity or recreational sport in your weekly routine."),
    ("PHY", "SPO", "everyday activity and recreational sport", "Pick one activity you genuinely enjoy rather than adding targets."),
    ("SOC", "CIV", "social connection and community participation", "A small volunteering activity can build belonging and community at the same time."),
    ("MUS", "SPI", "creative engagement and inner calm", "Quiet listening to music you love can double as a reflective pause."),
]
LOW = 60.0
DECLINE = 5.0


def _run_one(agent_id: str, assessment_id: uuid.UUID, run_id: uuid.UUID, max_retries: int) -> tuple[str, str, str | None]:
    agent = get_agent(agent_id)
    last_err = None
    for attempt in range(1, max_retries + 1):
        db: Session = SessionLocal()
        started = time.perf_counter()
        try:
            agent.run(db, assessment_id)
            db.add(AgentExecutionLog(
                run_id=run_id, agent_id=agent.agent_id, assessment_id=assessment_id, attempt=attempt,
                status="succeeded", duration_ms=int((time.perf_counter() - started) * 1000),
            ))
            db.commit()
            return agent.agent_id, "succeeded", None
        except Exception as exc:  # noqa: BLE001 - every failure is logged and retried
            db.rollback()
            last_err = f"{type(exc).__name__}: {exc}"
            log.warning("agent %s attempt %d failed: %s", agent.agent_id, attempt, last_err)
            db.add(AgentExecutionLog(
                run_id=run_id, agent_id=agent.agent_id, assessment_id=assessment_id, attempt=attempt,
                status="failed", error_message=last_err[:2000],
                duration_ms=int((time.perf_counter() - started) * 1000),
            ))
            db.commit()
            if attempt < max_retries:
                time.sleep(0.2 * 2 ** (attempt - 1))
        finally:
            db.close()
    return agent.agent_id, "failed", last_err


def run_agents(
    assessment_id: uuid.UUID,
    agent_ids: list[str] | None = None,
    parallel: bool = True,
) -> dict:
    """Execute agents for an assessment. Safe to call from a background task."""
    s = get_settings()
    run_id = uuid.uuid4()
    with SessionLocal() as db:
        q = select(WellnessAgent).where(WellnessAgent.status == "active")
        agents = db.scalars(q).all()
        ids = [a.agent_id for a in agents if agent_ids is None or a.agent_id in agent_ids or a.category_id in agent_ids]
        seq = {a.agent_id for a in agents if a.execution_mode == "sequential"}
        sess = db.get(AssessmentSession, assessment_id)
        if sess is None:
            raise LookupError("assessment not found")
        sess.agents_status = "running"
        db.commit()

    results: dict[str, dict] = {}
    par_ids = [i for i in ids if i not in seq] if parallel else []
    seq_ids = [i for i in ids if i not in par_ids]
    if par_ids:
        with ThreadPoolExecutor(max_workers=min(7, len(par_ids))) as pool:
            futures = [pool.submit(_run_one, i, assessment_id, run_id, s.agent_max_retries) for i in par_ids]
            for f in as_completed(futures):
                aid, status, err = f.result()
                results[aid] = {"status": status, "error": err}
    for i in seq_ids:
        aid, status, err = _run_one(i, assessment_id, run_id, s.agent_max_retries)
        results[aid] = {"status": status, "error": err}

    with SessionLocal() as db:
        insights = build_cross_insights(db, assessment_id)
        sess = db.get(AssessmentSession, assessment_id)
        ok = sum(1 for r in results.values() if r["status"] == "succeeded")
        sess.agents_status = "completed" if ok == len(results) else ("partial" if ok else "failed")
        db.commit()
        status = sess.agents_status
    return {"run_id": str(run_id), "status": status, "agents": results, "insights": len(insights)}


def build_cross_insights(db: Session, assessment_id: uuid.UUID) -> list[CrossWellnessInsight]:
    sess = db.get(AssessmentSession, assessment_id)
    names = {c.category_id: c.category_name for c in db.scalars(select(WellnessCategory))}
    cur = {
        r.category_id: r.calculated_score
        for r in db.scalars(select(WellnessCategoryScore).where(WellnessCategoryScore.assessment_id == assessment_id))
    }
    prev_session = db.scalar(
        select(AssessmentSession)
        .where(
            AssessmentSession.user_id == sess.user_id,
            AssessmentSession.assessment_date < sess.assessment_date,
            AssessmentSession.completion_status == "completed",
            AssessmentSession.deleted_at.is_(None),
        )
        .order_by(AssessmentSession.assessment_date.desc())
        .limit(1)
    )
    prev = {}
    if prev_session:
        prev = {
            r.category_id: r.calculated_score
            for r in db.scalars(
                select(WellnessCategoryScore).where(WellnessCategoryScore.assessment_id == prev_session.assessment_id)
            )
        }

    db.execute(delete(CrossWellnessInsight).where(CrossWellnessInsight.assessment_id == assessment_id))
    usage: dict[str, int] = {}
    out: list[CrossWellnessInsight] = []
    for a, b, topic, suggestion in RELATIONS:
        sa, sb = cur.get(a), cur.get(b)
        if sa is None or sb is None or usage.get(a, 0) >= 2 or usage.get(b, 0) >= 2:
            continue
        pa, pb = prev.get(a), prev.get(b)
        kind = None
        if pa is not None and pb is not None and sa - pa <= -DECLINE and sb - pb <= -DECLINE:
            kind = "co_decline"
            msg = (
                f"Your {names[a]} ({pa:.0f}→{sa:.0f}) and {names[b]} ({pb:.0f}→{sb:.0f}) have both dropped since "
                f"your last assessment. Patterns in {topic} sometimes move together. {suggestion}"
            )
        elif sa < LOW and sb < LOW:
            kind = "co_low"
            msg = (
                f"Both {names[a]} ({sa:.0f}) and {names[b]} ({sb:.0f}) are below the Balanced range. "
                f"Patterns in {topic} can be connected for some people — this is an observation, not a cause. {suggestion}"
            )
        if kind:
            ins = CrossWellnessInsight(
                assessment_id=assessment_id, user_id=sess.user_id, categories=[a, b], insight_type=kind, message=msg,
                evidence={"current": {a: sa, b: sb}, "previous": {a: pa, b: pb} if prev else None},
            )
            db.add(ins)
            out.append(ins)
            usage[a] = usage.get(a, 0) + 1
            usage[b] = usage.get(b, 0) + 1
    db.flush()
    return out
