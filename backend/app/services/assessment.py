"""Transactional assessment submission and score calculation."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import (
    AssessmentResponse,
    AssessmentSession,
    CategoryComment,
    WellnessCategory,
    WellnessCategoryScore,
    WellnessParameter,
)
from . import scoring
from .safety import detect_crisis


def period_for(d: date | datetime) -> str:
    return f"{d.year}-Q{(d.month - 1) // 3 + 1}"


@dataclass
class Answer:
    parameter_id: str
    value: int | None
    status: str = "answered"  # answered | not_applicable | prefer_not_to_answer
    comment: str | None = None


def _validate(answers: list[Answer], params: dict[str, WellnessParameter]) -> None:
    seen = set()
    for a in answers:
        p = params.get(a.parameter_id)
        if p is None:
            raise HTTPException(422, f"Unknown or inactive parameter {a.parameter_id}")
        if a.parameter_id in seen:
            raise HTTPException(422, f"Duplicate answer for {a.parameter_id}")
        seen.add(a.parameter_id)
        if a.status == "answered":
            allowed = {o["value"] for o in p.options}
            if a.value not in allowed:
                raise HTTPException(422, f"Invalid value {a.value} for {a.parameter_id}")
        elif a.status == "not_applicable":
            if not p.allow_not_applicable:
                raise HTTPException(422, f"'Not applicable' is not available for {a.parameter_id}")
            a.value = None
        elif a.status == "prefer_not_to_answer":
            a.value = None
        else:
            raise HTTPException(422, f"Invalid response status {a.status}")


def compute_category_scores(db: Session, session: AssessmentSession) -> list[scoring.CategoryResult]:
    """(Re)compute and upsert category scores + overall indicator for a session."""
    levels = scoring.get_levels(db)
    cfg = scoring.get_scoring_config(db)
    categories = db.scalars(
        select(WellnessCategory).where(WellnessCategory.is_active).order_by(WellnessCategory.display_order)
    ).all()
    resp_by_param = {
        r.parameter_id: r
        for r in db.scalars(
            select(AssessmentResponse).where(AssessmentResponse.assessment_id == session.assessment_id)
        )
    }
    results = []
    for cat in categories:
        items = [
            scoring.ItemResult(
                p.parameter_id,
                p.parameter_weightage,
                resp_by_param[p.parameter_id].normalized_score if p.parameter_id in resp_by_param else None,
            )
            for p in cat.parameters
            if p.is_active
        ]
        res = scoring.score_category(
            cat.category_id, items, cat.target_score, levels, cfg["min_category_coverage"]
        )
        results.append(res)
        row = db.scalar(
            select(WellnessCategoryScore).where(
                WellnessCategoryScore.assessment_id == session.assessment_id,
                WellnessCategoryScore.category_id == cat.category_id,
            )
        )
        if row is None:
            row = WellnessCategoryScore(
                assessment_id=session.assessment_id, user_id=session.user_id, category_id=cat.category_id
            )
            db.add(row)
        row.calculated_score = res.score
        row.wellness_level = res.level
        row.target_score = res.target
        row.score_gap = res.gap
        row.coverage = res.coverage
        row.answered_count = res.answered
        row.calculated_date = datetime.now(timezone.utc)

    weights = {c.category_id: c.default_weightage for c in categories}
    session.overall_indicator = scoring.overall_indicator(results, weights, cfg["min_categories_for_overall"])
    total_items = sum(r.total for r in results)
    session.coverage = round(sum(r.answered for r in results) / total_items, 2) if total_items else 0
    return results


def submit_assessment(
    db: Session,
    user_id: uuid.UUID,
    answers: list[Answer],
    category_comments: dict[str, str] | None = None,
    source: str = "self",
    interviewer_id: uuid.UUID | None = None,
    assessment_date: datetime | None = None,
) -> tuple[AssessmentSession, bool]:
    """Create a complete assessment atomically. Returns (session, crisis_flag)."""
    params = {
        p.parameter_id: p
        for p in db.scalars(select(WellnessParameter).where(WellnessParameter.is_active))
    }
    _validate(answers, params)
    if not answers:
        raise HTTPException(422, "At least one answer is required")

    when = assessment_date or datetime.now(timezone.utc)
    prior = db.scalar(
        select(func.count()).select_from(AssessmentSession).where(
            AssessmentSession.user_id == user_id,
            AssessmentSession.completion_status == "completed",
            AssessmentSession.deleted_at.is_(None),
        )
    )
    try:
        session = AssessmentSession(
            user_id=user_id,
            assessment_type="baseline" if prior == 0 else "quarterly",
            assessment_date=when,
            assessment_period=period_for(when),
            completion_status="completed",
            assessment_source=source,
            interviewer_id=interviewer_id,
        )
        db.add(session)
        db.flush()
        for a in answers:
            p = params[a.parameter_id]
            db.add(
                AssessmentResponse(
                    assessment_id=session.assessment_id,
                    parameter_id=a.parameter_id,
                    response_value=a.value,
                    response_status=a.status,
                    normalized_score=scoring.normalize(a.value, p.scoring_rule.get("reverse", False)),
                    comments=a.comment,
                    response_date=when,
                )
            )
        for cat_id, text in (category_comments or {}).items():
            if text and text.strip():
                db.add(CategoryComment(assessment_id=session.assessment_id, category_id=cat_id, comment=text.strip()[:2000]))
        db.flush()
        compute_category_scores(db, session)
        db.commit()
    except Exception:
        db.rollback()
        raise
    crisis = detect_crisis(*(category_comments or {}).values(), *(a.comment for a in answers))
    return session, crisis
