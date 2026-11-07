"""Quarterly review engine and reminder/notification generation."""
from __future__ import annotations

import uuid
from datetime import date, timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import (
    HabitLog,
    MicroHabit,
    Notification,
    QuarterlyReview,
    User,
    UserPreference,
    WellnessCategory,
)
from .dashboard import agent_outputs, compare, completed_sessions


def create_review(db: Session, user_id: uuid.UUID, coach_id: uuid.UUID | None = None) -> QuarterlyReview:
    sessions = completed_sessions(db, user_id)
    if not sessions:
        raise HTTPException(400, "Complete an assessment before creating a quarterly review.")
    current = sessions[-1]
    existing = db.scalar(select(QuarterlyReview).where(QuarterlyReview.current_assessment_id == current.assessment_id))
    if existing:
        return existing
    previous = sessions[-2] if len(sessions) > 1 else None
    cats = db.scalars(select(WellnessCategory).where(WellnessCategory.is_active).order_by(WellnessCategory.display_order)).all()
    rows = compare(db, sessions[0].assessment_id, previous.assessment_id if previous else None, current.assessment_id, cats)
    outputs = agent_outputs(db, current.assessment_id)
    for r in rows:
        out = outputs.get(r["category_id"], {})
        r["next_quarter_target"] = out.get("target_score")
        r["next_quarter_actions"] = [a["title"] for a in out.get("recommended_actions", [])]

    changes = [r["change"] for r in rows if r["change"] is not None]
    progress = round(sum(changes) / len(changes), 1) if changes else None
    improved = [r["category_name"] for r in rows if r["direction"] == "improved"]
    declined = [r["category_name"] for r in rows if r["direction"] == "declined"]
    if previous is None:
        summary = "This is your baseline review. Future quarterly reviews will show how each dimension changes over time."
    else:
        parts = [f"Compared with {previous.assessment_period}:"]
        parts.append(f"{len(improved)} dimension(s) improved" + (f" ({', '.join(improved)})" if improved else "") + ".")
        if declined:
            parts.append(f"{len(declined)} dimension(s) declined ({', '.join(declined)}) — worth gentle attention next quarter.")
        parts.append("Remember: the goal is sustainable progress, not perfection.")
        summary = " ".join(parts)

    d = current.assessment_date.date()
    review = QuarterlyReview(
        user_id=user_id, quarter=(d.month - 1) // 3 + 1, year=d.year,
        previous_assessment_id=previous.assessment_id if previous else None,
        current_assessment_id=current.assessment_id, overall_progress=progress,
        comparison={"rows": rows, "improved": improved, "declined": declined,
                    "baseline_period": sessions[0].assessment_period,
                    "previous_period": previous.assessment_period if previous else None,
                    "current_period": current.assessment_period},
        review_summary=summary, coach_id=coach_id,
    )
    db.add(review)
    try:
        db.commit()
    except IntegrityError:  # concurrent creation
        db.rollback()
        return db.scalar(select(QuarterlyReview).where(QuarterlyReview.current_assessment_id == current.assessment_id))
    return review


def _notify(db: Session, user_id, kind, title, message, key) -> None:
    if db.scalar(select(Notification).where(Notification.user_id == user_id, Notification.dedupe_key == key)):
        return
    db.add(Notification(user_id=user_id, notification_type=kind, title=title, message=message, dedupe_key=key))


def generate_notifications(db: Session, user: User) -> None:
    """Idempotent reminder engine (also runnable for all users via the admin/cron endpoint)."""
    if user.user_role != "individual":
        return
    sessions = completed_sessions(db, user.user_id)
    today = date.today()
    if not sessions:
        _notify(db, user.user_id, "assessment_due", "Start your baseline assessment",
                "A short check-in across 14 dimensions — about 10 minutes.", "baseline")
    else:
        due = sessions[-1].assessment_date.date() + timedelta(days=get_settings().review_interval_days)
        if due <= today + timedelta(days=7):
            _notify(db, user.user_id, "quarterly_due", "Quarterly check-in is due",
                    f"Your next reassessment is due on {due.isoformat()}. It reuses the same short questions so you can see real change.",
                    f"quarterly:{due.isoformat()}")
    pref = db.scalar(select(UserPreference).where(UserPreference.user_id == user.user_id))
    if pref is None or pref.reminders_enabled:
        habits = db.scalars(select(MicroHabit).where(MicroHabit.user_id == user.user_id, MicroHabit.status == "active", MicroHabit.frequency == "daily"))
        for h in habits:
            done = db.scalar(select(HabitLog).where(HabitLog.habit_id == h.habit_id, HabitLog.log_date == today))
            if not done and h.reminder_time:
                _notify(db, user.user_id, "habit_reminder", f"Gentle reminder: {h.habit_name}",
                        "Only if it suits your day — skipping is fine.", f"habit:{h.habit_id}:{today.isoformat()}")
    db.commit()
