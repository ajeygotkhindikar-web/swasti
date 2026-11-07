"""Builds the 360° dashboard and quarterly comparisons from database records."""
from __future__ import annotations

import uuid
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import (
    AgentAssessment,
    AssessmentSession,
    CrossWellnessInsight,
    HabitLog,
    MicroHabit,
    QuarterlyReview,
    WellnessCategory,
    WellnessCategoryScore,
)

IMPROVE = 2.0


def completed_sessions(db: Session, user_id: uuid.UUID) -> list[AssessmentSession]:
    return list(
        db.scalars(
            select(AssessmentSession)
            .where(
                AssessmentSession.user_id == user_id,
                AssessmentSession.completion_status == "completed",
                AssessmentSession.deleted_at.is_(None),
            )
            .order_by(AssessmentSession.assessment_date)
        )
    )


def scores_for(db: Session, assessment_id: uuid.UUID | None) -> dict[str, WellnessCategoryScore]:
    if assessment_id is None:
        return {}
    return {
        r.category_id: r
        for r in db.scalars(select(WellnessCategoryScore).where(WellnessCategoryScore.assessment_id == assessment_id))
    }


def agent_outputs(db: Session, assessment_id: uuid.UUID | None) -> dict[str, dict]:
    if assessment_id is None:
        return {}
    rows = db.scalars(
        select(AgentAssessment)
        .where(AgentAssessment.assessment_id == assessment_id, AgentAssessment.execution_status == "succeeded")
        .order_by(AgentAssessment.execution_timestamp)
    )
    return {r.output["category_id"]: r.output for r in rows}


def _val(row):
    return row.calculated_score if row is not None else None


def compare(db: Session, baseline, previous, current, categories) -> list[dict]:
    b, p, c = scores_for(db, baseline), scores_for(db, previous), scores_for(db, current)
    out = []
    for cat in categories:
        cs, ps, bs = _val(c.get(cat.category_id)), _val(p.get(cat.category_id)), _val(b.get(cat.category_id))
        change = round(cs - ps, 1) if cs is not None and ps is not None else None
        direction = None
        if change is not None:
            direction = "improved" if change > IMPROVE else "declined" if change < -IMPROVE else "steady"
        out.append({
            "category_id": cat.category_id,
            "category_name": cat.category_name,
            "baseline": bs,
            "previous": ps,
            "current": cs,
            "target": cat.target_score,
            "change": change,
            "direction": direction,
            "level": c[cat.category_id].wellness_level if cat.category_id in c else None,
        })
    return out


def build_dashboard(db: Session, user_id: uuid.UUID) -> dict:
    cats = db.scalars(
        select(WellnessCategory).where(WellnessCategory.is_active).order_by(WellnessCategory.display_order)
    ).all()
    sessions = completed_sessions(db, user_id)
    latest = sessions[-1] if sessions else None
    previous = sessions[-2] if len(sessions) > 1 else None
    baseline = sessions[0] if sessions else None
    outputs = agent_outputs(db, latest.assessment_id if latest else None)
    cur = scores_for(db, latest.assessment_id if latest else None)
    comparison = compare(
        db,
        baseline.assessment_id if baseline else None,
        previous.assessment_id if previous else None,
        latest.assessment_id if latest else None,
        cats,
    )

    cards = []
    for cat, cmp in zip(cats, comparison):
        out = outputs.get(cat.category_id, {})
        row = cur.get(cat.category_id)
        cards.append({
            **cmp,
            "icon": cat.category_icon,
            "description": cat.category_description,
            "coverage": row.coverage if row else None,
            "achievable_target": out.get("target_score"),
            "summary": out.get("progress_report"),
            "confidence": out.get("confidence_level"),
        })

    assessed = [c for c in cards if c["current"] is not None]
    next_review = (latest.assessment_date.date() + timedelta(days=get_settings().review_interval_days)) if latest else None

    trend = []
    for s in sessions:
        sc = scores_for(db, s.assessment_id)
        trend.append({
            "assessment_id": str(s.assessment_id),
            "period": s.assessment_period,
            "date": s.assessment_date.date().isoformat(),
            "overall": s.overall_indicator,
            **{cid: r.calculated_score for cid, r in sc.items()},
        })

    # Micro-habit completion trend: completions per week, last 12 weeks
    since = date.today() - timedelta(weeks=12)
    logs = db.execute(
        select(HabitLog.log_date, func.count())
        .join(MicroHabit, MicroHabit.habit_id == HabitLog.habit_id)
        .where(MicroHabit.user_id == user_id, HabitLog.log_date >= since)
        .group_by(HabitLog.log_date)
    ).all()
    weekly: dict[str, int] = {}
    for d, n in logs:
        wk = (d - timedelta(days=d.weekday())).isoformat()
        weekly[wk] = weekly.get(wk, 0) + n
    habit_trend = [{"week": k, "completions": v} for k, v in sorted(weekly.items())]

    # Top 5 priorities: largest gap to target among scored categories
    priorities = sorted(
        [c for c in assessed if c["current"] < c["target"]], key=lambda c: c["current"] - c["target"]
    )[:5]
    priority_items = []
    for p in priorities:
        out = outputs.get(p["category_id"], {})
        priority_items.append({
            "category_id": p["category_id"],
            "category_name": p["category_name"],
            "current": p["current"],
            "target": out.get("target_score", p["target"]),
            "level": p["level"],
            "actions": out.get("recommended_actions", [])[:2],
            "micro_habits": out.get("suggested_micro_habits", [])[:2],
        })
    all_habits = [h | {"category_id": cid} for cid, o in outputs.items() for h in o.get("suggested_micro_habits", [])]

    insights = []
    if latest:
        insights = [
            {"categories": i.categories, "type": i.insight_type, "message": i.message, "evidence": i.evidence}
            for i in db.scalars(select(CrossWellnessInsight).where(CrossWellnessInsight.assessment_id == latest.assessment_id))
        ]
    safety = next((o["safety"] for o in outputs.values() if o.get("safety")), None)
    last_review = db.scalar(
        select(QuarterlyReview).where(QuarterlyReview.user_id == user_id).order_by(QuarterlyReview.review_date.desc()).limit(1)
    )

    return {
        "has_data": latest is not None,
        "overview": {
            "overall_indicator": latest.overall_indicator if latest else None,
            "coverage": latest.coverage if latest else None,
            "dimensions_assessed": len(assessed),
            "dimensions_total": len(cats),
            "needs_attention": sum(1 for c in assessed if c["level"] == "Needs Attention"),
            "improving": sum(1 for c in assessed if c["direction"] == "improved"),
            "declining": sum(1 for c in assessed if c["direction"] == "declined"),
            "last_assessment_date": latest.assessment_date.date().isoformat() if latest else None,
            "next_review_date": next_review.isoformat() if next_review else None,
            "review_due": bool(next_review and next_review <= date.today()),
            "assessments_count": len(sessions),
            "agents_status": latest.agents_status if latest else None,
            "latest_assessment_id": str(latest.assessment_id) if latest else None,
            "last_review_id": str(last_review.review_id) if last_review else None,
        },
        "attention_flags": [
            {"category_id": c["category_id"], "category_name": c["category_name"], "score": c["current"]}
            for c in assessed if c["level"] == "Needs Attention"
        ],
        "cards": cards,
        "radar": [
            {
                "category_id": c["category_id"],
                "category": c["category_name"].replace(" Wellness", ""),
                "baseline": c["baseline"],
                "previous": c["previous"],
                "current": c["current"],
                "target": c["target"],
            }
            for c in cards
        ],
        "trend": trend,
        "habit_trend": habit_trend,
        "priorities": priority_items,
        "daily_habits": [h for h in all_habits if h["frequency"] == "daily"][:6],
        "weekly_habits": [h for h in all_habits if h["frequency"] == "weekly"][:6],
        "insights": insights,
        "safety": safety,
        "disclaimer": "Wellness scores are self-assessment indicators, not medical diagnoses or professional financial assessments.",
    }
