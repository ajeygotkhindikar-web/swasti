"""Transparent, configurable wellness scoring engine.

* Each answered item is normalised to 0–100: (value − 1) / 4 × 100, reversed
  for items where a higher frequency is less healthy.
* "Not applicable" and "prefer not to answer" are excluded, never zero.
* Category score = Σ(score × weight) / Σ(weights of answered items).
* A category with coverage below the configured minimum gets no score
  ("Insufficient data") rather than a misleading number.
* The overall indicator is only produced when enough categories are scored,
  and categories needing attention are always surfaced separately, so a high
  score in one dimension can't hide a concern in another.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from ..models import SystemSetting
from ..seed.master_data import DEFAULT_LEVELS, DEFAULT_SCORING

INSUFFICIENT = "Insufficient data"


def normalize(value: int | None, reverse: bool = False) -> float | None:
    if value is None:
        return None
    if not 1 <= value <= 5:
        raise ValueError(f"response value {value} outside 1..5")
    score = (value - 1) / 4 * 100
    return round(100 - score if reverse else score, 2)


def get_levels(db: Session | None) -> list[dict]:
    if db is not None:
        row = db.get(SystemSetting, "wellness_levels")
        if row:
            return row.value
    return DEFAULT_LEVELS


def get_scoring_config(db: Session | None) -> dict:
    cfg = dict(DEFAULT_SCORING)
    if db is not None:
        row = db.get(SystemSetting, "scoring_config")
        if row:
            cfg.update(row.value)
    return cfg


def level_for(score: float | None, levels: list[dict]) -> str:
    if score is None:
        return INSUFFICIENT
    for band in levels:
        if band["min"] <= score <= band["max"]:
            return band["level"]
    return levels[-1]["level"] if score > levels[-1]["max"] else levels[0]["level"]


@dataclass
class ItemResult:
    parameter_id: str
    weight: float
    normalized: float | None  # None = excluded (NA / prefer not / unanswered)


@dataclass
class CategoryResult:
    category_id: str
    score: float | None
    level: str
    coverage: float
    answered: int
    total: int
    target: float
    gap: float | None
    items: list[ItemResult] = field(default_factory=list)


def score_category(
    category_id: str,
    items: list[ItemResult],
    target: float,
    levels: list[dict],
    min_coverage: float,
) -> CategoryResult:
    total = len(items)
    answered = [i for i in items if i.normalized is not None]
    coverage = round(len(answered) / total, 2) if total else 0.0
    score = None
    if answered and coverage >= min_coverage:
        wsum = sum(i.weight for i in answered)
        score = round(sum(i.normalized * i.weight for i in answered) / wsum, 1)
    gap = round(max(target - score, 0), 1) if score is not None else None
    return CategoryResult(
        category_id, score, level_for(score, levels), coverage, len(answered), total, target, gap, items
    )


def overall_indicator(
    results: list[CategoryResult], weights: dict[str, float], min_categories: int
) -> float | None:
    scored = [r for r in results if r.score is not None]
    if len(scored) < min_categories:
        return None
    wsum = sum(weights.get(r.category_id, 1.0) for r in scored)
    if wsum == 0:
        return None
    return round(sum(r.score * weights.get(r.category_id, 1.0) for r in scored) / wsum, 1)


def achievable_target(score: float | None, category_target: float, step: float) -> float:
    """A realistic next-quarter target: progress, not perfection."""
    if score is None:
        return category_target
    if score >= category_target:
        return round(min(score, 100), 1)  # maintain
    return round(min(category_target, score + step), 1)
