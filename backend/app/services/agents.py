"""Fourteen specialised, independently executable wellness agents.

Each agent:
 1. fetches the individual's responses for one category,
 2. retrieves the category's history,
 3. (re)calculates the category score with the shared scoring engine,
 4. identifies strengths and 5. improvement areas at item level,
 6. compares against the configurable benchmark (category target),
 7. sets an achievable next-quarter target,
 8. selects evidence-linked recommendations from the knowledge base,
 9. suggests micro-habits,
10. writes a concise progress report, and
11. saves a structured result (AgentAssessment).

Recommendations come only from the curated knowledge base, each carrying a
reference. Optional LLM wording (when ANTHROPIC_API_KEY is set and the person
consented to AI analysis) can only rephrase the deterministic summary; it is
labelled as AI-generated and never changes scores, answers or the choice of
recommendations. Agents never diagnose, prescribe, or recommend investment
products.
"""
from __future__ import annotations

import logging
import uuid
from typing import ClassVar

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import (
    AgentAssessment,
    AssessmentResponse,
    AssessmentSession,
    CategoryComment,
    ScientificReference,
    WellnessAgent,
    WellnessCategory,
    WellnessCategoryScore,
    WellnessParameter,
    WellnessRecommendation,
)
from . import scoring
from .safety import CRISIS_GUIDANCE, detect_crisis

log = logging.getLogger("swasti.agents")

BOUNDARY = (
    "This is a self-assessment indicator, not a medical, psychological or financial diagnosis."
)


class WellnessAgentBase:
    category_id: ClassVar[str]
    agent_id: ClassVar[str]
    name: ClassVar[str]
    version: ClassVar[str] = "1.0.0"
    guardrail: ClassVar[str] = BOUNDARY
    strength_threshold: ClassVar[float] = 75.0
    improvement_threshold: ClassVar[float] = 50.0

    # ------------------------------------------------------------ helpers
    def _load(self, db: Session, assessment_id: uuid.UUID):
        session = db.get(AssessmentSession, assessment_id)
        if session is None:
            raise LookupError(f"assessment {assessment_id} not found")
        category = db.get(WellnessCategory, self.category_id)
        params = [p for p in category.parameters if p.is_active]
        responses = {
            r.parameter_id: r
            for r in db.scalars(
                select(AssessmentResponse).where(
                    AssessmentResponse.assessment_id == assessment_id,
                    AssessmentResponse.parameter_id.in_([p.parameter_id for p in params]),
                )
            )
        }
        comment = db.scalar(
            select(CategoryComment.comment).where(
                CategoryComment.assessment_id == assessment_id,
                CategoryComment.category_id == self.category_id,
            )
        )
        return session, category, params, responses, comment

    def _history(self, db: Session, session: AssessmentSession) -> list[dict]:
        rows = db.execute(
            select(WellnessCategoryScore.calculated_score, AssessmentSession.assessment_date, AssessmentSession.assessment_period)
            .join(AssessmentSession, AssessmentSession.assessment_id == WellnessCategoryScore.assessment_id)
            .where(
                WellnessCategoryScore.user_id == session.user_id,
                WellnessCategoryScore.category_id == self.category_id,
                AssessmentSession.assessment_date < session.assessment_date,
                AssessmentSession.deleted_at.is_(None),
            )
            .order_by(AssessmentSession.assessment_date)
        ).all()
        return [{"score": r[0], "date": r[1].isoformat(), "period": r[2]} for r in rows]

    def specialised_notes(self, ctx: dict) -> list[str]:
        """Category-specific observations. Overridden by specialised agents."""
        return []

    def select_recommendations(
        self, db: Session, improvement_ids: list[str], below_target: bool
    ) -> list[WellnessRecommendation]:
        recs = db.scalars(
            select(WellnessRecommendation).where(
                WellnessRecommendation.category_id == self.category_id, WellnessRecommendation.is_active
            )
        ).all()

        def rank(r: WellnessRecommendation):
            overlap = len(set(r.target_parameters or []) & set(improvement_ids))
            return (-overlap, r.recommendation_priority, r.recommendation_id)

        ranked = sorted(recs, key=rank)
        return ranked[: 3 if below_target else 1]

    # ------------------------------------------------------------ main entry
    def run(self, db: Session, assessment_id: uuid.UUID) -> dict:
        session, category, params, responses, comment = self._load(db, assessment_id)
        levels = scoring.get_levels(db)
        cfg = scoring.get_scoring_config(db)

        items = [
            scoring.ItemResult(
                p.parameter_id,
                p.parameter_weightage,
                responses[p.parameter_id].normalized_score if p.parameter_id in responses else None,
            )
            for p in params
        ]
        result = scoring.score_category(
            self.category_id, items, category.target_score, levels, cfg["min_category_coverage"]
        )
        score_row = db.scalar(
            select(WellnessCategoryScore).where(
                WellnessCategoryScore.assessment_id == assessment_id,
                WellnessCategoryScore.category_id == self.category_id,
            )
        )
        if score_row is None:
            score_row = WellnessCategoryScore(
                assessment_id=assessment_id, user_id=session.user_id, category_id=self.category_id
            )
            db.add(score_row)
        score_row.calculated_score = result.score
        score_row.wellness_level = result.level
        score_row.target_score = result.target
        score_row.score_gap = result.gap
        score_row.coverage = result.coverage
        score_row.answered_count = result.answered
        db.flush()

        pname = {p.parameter_id: p.parameter_name for p in params}
        answered = [i for i in items if i.normalized is not None]
        strengths = [
            {"parameter_id": i.parameter_id, "name": pname[i.parameter_id], "score": i.normalized}
            for i in sorted(answered, key=lambda i: -i.normalized)
            if i.normalized >= self.strength_threshold
        ]
        improvements = [
            {"parameter_id": i.parameter_id, "name": pname[i.parameter_id], "score": i.normalized}
            for i in sorted(answered, key=lambda i: i.normalized)
            if i.normalized <= self.improvement_threshold
        ]
        history = self._history(db, session)
        prev = next((h["score"] for h in reversed(history) if h["score"] is not None), None)
        change = round(result.score - prev, 1) if result.score is not None and prev is not None else None
        target_next = scoring.achievable_target(result.score, category.target_score, cfg["quarterly_step"])
        below_target = result.score is None or result.score < category.target_score

        recs = self.select_recommendations(db, [i["parameter_id"] for i in improvements], below_target)
        ref_ids = {r.evidence_reference for r in recs}
        refs = {
            r.reference_id: r
            for r in db.scalars(select(ScientificReference).where(ScientificReference.reference_id.in_(ref_ids)))
        }
        actions = [
            {
                "recommendation_id": r.recommendation_id,
                "title": r.recommendation_title,
                "action": r.recommended_action,
                "rationale": r.recommendation_description,
                "frequency": r.suggested_frequency,
                "addresses": [pname.get(p, p) for p in (r.target_parameters or []) if p in pname],
                "evidence_reference": r.evidence_reference,
            }
            for r in recs
        ]
        habits = [
            {"recommendation_id": r.recommendation_id, "habit": r.micro_habit, "frequency": r.suggested_frequency}
            for r in recs
        ]
        evidence = [
            {
                "reference_id": ref.reference_id,
                "title": ref.reference_title,
                "organization": ref.issuing_organization,
                "url": ref.reference_url,
                "verification_status": ref.verification_status,
                "last_verified_date": ref.last_verified_date.isoformat() if ref.last_verified_date else None,
            }
            for ref in refs.values()
        ]
        confidence = "high" if result.coverage >= 0.75 else "medium" if result.coverage >= 0.5 else "low"
        review_days = 30 if result.level == "Needs Attention" else 90

        ctx = {
            "result": result,
            "improvements": improvements,
            "responses": responses,
            "comment": comment,
            "session": session,
        }
        notes = self.specialised_notes(ctx)
        safety = None
        if detect_crisis(comment):
            safety = CRISIS_GUIDANCE
            notes.append("Free-text comment suggests possible serious distress; crisis resources shown and human follow-up advised.")

        summary = self._summary(category.category_name, result, prev, change, strengths, improvements, target_next)
        output = {
            "user_id": str(session.user_id),
            "assessment_id": str(assessment_id),
            "category_id": self.category_id,
            "agent_id": self.agent_id,
            "agent_version": self.version,
            "current_score": result.score,
            "current_level": result.level,
            "coverage": result.coverage,
            "previous_score": prev,
            "change_since_previous": change,
            "benchmark_target": category.target_score,
            "target_score": target_next,
            "target_level": scoring.level_for(target_next, levels),
            "strengths": strengths,
            "improvement_areas": improvements,
            "recommended_actions": actions,
            "suggested_micro_habits": habits,
            "evidence_references": evidence,
            "confidence_level": confidence,
            "review_interval_days": review_days,
            "progress_report": summary,
            "specialised_notes": notes,
            "safety": safety,
            "disclaimer": self.guardrail,
            "ai_narrative": None,
        }
        narrative = self._llm_narrative(output, category.category_name, session.user_id, db)
        if narrative:
            output["ai_narrative"] = {"text": narrative, "label": "AI-generated wording; scores and recommendations unchanged."}

        existing = db.scalar(
            select(AgentAssessment).where(
                AgentAssessment.assessment_id == assessment_id,
                AgentAssessment.agent_id == self.agent_id,
                AgentAssessment.agent_version == self.version,
            )
        )
        row = existing or AgentAssessment(
            agent_id=self.agent_id, agent_version=self.version, assessment_id=assessment_id
        )
        row.category_score_id = score_row.category_score_id
        row.analysis_summary = summary
        row.identified_gaps = [i["name"] for i in improvements]
        row.recommendation_summary = "; ".join(a["title"] for a in actions) or "Maintain current habits."
        row.output = output
        row.confidence_level = confidence
        row.execution_status = "succeeded"
        if existing is None:
            db.add(row)
        db.commit()
        return output

    def _summary(self, name, result, prev, change, strengths, improvements, target_next) -> str:
        if result.score is None:
            return (
                f"{name}: not enough answers to calculate a reliable score "
                f"({result.answered} of {result.total} answered). Answer a few more questions next time for a clearer picture."
            )
        parts = [f"{name} is at {result.score:.0f}/100 ({result.level})."]
        if change is not None:
            if change > 2:
                parts.append(f"That's up {change:.0f} points since your last assessment — well done.")
            elif change < -2:
                parts.append(f"That's {abs(change):.0f} points lower than last time.")
            else:
                parts.append("That's broadly steady since your last assessment.")
        if strengths:
            parts.append("Strengths: " + ", ".join(s["name"].lower() for s in strengths[:2]) + ".")
        if improvements:
            parts.append("Most room to grow: " + ", ".join(i["name"].lower() for i in improvements[:2]) + ".")
        if result.score < result.target:
            parts.append(f"An achievable next-quarter target is {target_next:.0f}.")
        else:
            parts.append("You're at or above the benchmark — focus on sustaining what works.")
        return " ".join(parts)

    def _llm_narrative(self, output: dict, name: str, user_id: uuid.UUID, db: Session) -> str | None:
        s = get_settings()
        if not s.anthropic_api_key:
            return None
        from ..models import ConsentRecord  # local import to avoid cycle

        consent = db.scalar(
            select(ConsentRecord).where(
                ConsentRecord.user_id == user_id,
                ConsentRecord.consent_type == "ai_analysis",
                ConsentRecord.granted_status,
                ConsentRecord.withdrawal_timestamp.is_(None),
            )
        )
        if consent is None:
            return None
        # Data minimisation: no name, email, free-text or identifiers leave the system.
        facts = {
            "dimension": name,
            "score": output["current_score"],
            "level": output["current_level"],
            "change": output["change_since_previous"],
            "strengths": [x["name"] for x in output["strengths"]],
            "improvement_areas": [x["name"] for x in output["improvement_areas"]],
            "actions": [a["title"] for a in output["recommended_actions"]],
        }
        prompt = (
            "Rewrite these wellness self-assessment facts as 2-3 warm, encouraging sentences for the person. "
            "Use only the facts given; do not add advice, numbers, diagnoses, medication, or financial products. "
            f"Facts: {facts}"
        )
        try:
            r = httpx.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": s.anthropic_api_key, "anthropic-version": "2023-06-01"},
                json={"model": s.llm_model, "max_tokens": 200, "messages": [{"role": "user", "content": prompt}]},
                timeout=20,
            )
            r.raise_for_status()
            return "".join(b.get("text", "") for b in r.json().get("content", [])).strip() or None
        except Exception as exc:  # LLM wording is optional; never fail the agent on it
            log.warning("LLM narrative unavailable: %s", exc)
            return None


# ---------------------------------------------------------------- specialised agents
class MentalWellnessAgent(WellnessAgentBase):
    category_id, agent_id, name = "MEN", "mental_agent", "Mental Wellness Agent"

    def specialised_notes(self, ctx):
        notes = []
        r = ctx["responses"].get("MEN_01")
        if r and r.response_value and r.response_value >= 4:
            notes.append("Work-related stress is reported as frequent. If it persists or feels unmanageable, consider speaking with a qualified professional.")
        return notes


class PhysicalWellnessAgent(WellnessAgentBase):
    category_id, agent_id, name = "PHY", "physical_agent", "Physical Wellness Agent"
    guardrail = BOUNDARY + " Consult a doctor before starting a new exercise programme if you have a health condition."


class FinancialWellnessAgent(WellnessAgentBase):
    category_id, agent_id, name = "FIN", "financial_agent", "Financial Wellness Agent"
    guardrail = BOUNDARY + " SWASTI does not recommend investment or insurance products; consult a SEBI-registered adviser for personal advice."

    def specialised_notes(self, ctx):
        r = ctx["responses"].get("FIN_02")
        if r and r.response_status == "not_applicable":
            return ["No current loans reported; loan burden excluded from the score."]
        return []


class PsychologicalWellnessAgent(WellnessAgentBase):
    category_id, agent_id, name = "PSY", "psychological_agent", "Psychological Wellness Agent"

    def specialised_notes(self, ctx):
        res = ctx["result"]
        if res.score is not None and res.score < 40:
            return ["Several psychological indicators are low. Talking to a qualified counsellor can help; Tele-MANAS (14416) offers free support."]
        return []


class SocialWellnessAgent(WellnessAgentBase):
    category_id, agent_id, name = "SOC", "social_agent", "Social Wellness Agent"


class SpiritualWellnessAgent(WellnessAgentBase):
    category_id, agent_id, name = "SPI", "spiritual_agent", "Spiritual Wellness Agent"
    guardrail = BOUNDARY + " Suggestions are open to any belief system, or none."


class FamilyWellnessAgent(WellnessAgentBase):
    category_id, agent_id, name = "FAM", "family_agent", "Family Wellness Agent"

    def specialised_notes(self, ctx):
        r = ctx["responses"].get("FAM_04")
        if r and r.response_status == "not_applicable":
            return ["Children/dependents question marked not applicable and excluded."]
        return []


class MusicalWellnessAgent(WellnessAgentBase):
    category_id, agent_id, name = "MUS", "musical_agent", "Musical Wellness Agent"


class EnvironmentalWellnessAgent(WellnessAgentBase):
    category_id, agent_id, name = "ENV", "environmental_agent", "Environmental Wellness Agent"


class CivicWellnessAgent(WellnessAgentBase):
    category_id, agent_id, name = "CIV", "civic_agent", "Civic Wellness Agent"


class EmpatheticWellnessAgent(WellnessAgentBase):
    category_id, agent_id, name = "EMP", "empathetic_agent", "Empathetic Wellness Agent"


class SportingWellnessAgent(WellnessAgentBase):
    category_id, agent_id, name = "SPO", "sporting_agent", "Sporting Wellness Agent"
    guardrail = BOUNDARY + " There are no performance comparisons — any enjoyable activity counts."


class CulturalWellnessAgent(WellnessAgentBase):
    category_id, agent_id, name = "CUL", "cultural_agent", "Cultural Wellness Agent"


class UniversalBrotherhoodAgent(WellnessAgentBase):
    category_id, agent_id, name = "UNI", "brotherhood_agent", "Universal Brotherhood Agent"


AGENT_CLASSES: list[type[WellnessAgentBase]] = [
    MentalWellnessAgent, PhysicalWellnessAgent, FinancialWellnessAgent, PsychologicalWellnessAgent,
    SocialWellnessAgent, SpiritualWellnessAgent, FamilyWellnessAgent, MusicalWellnessAgent,
    EnvironmentalWellnessAgent, CivicWellnessAgent, EmpatheticWellnessAgent, SportingWellnessAgent,
    CulturalWellnessAgent, UniversalBrotherhoodAgent,
]
REGISTRY: dict[str, type[WellnessAgentBase]] = {c.category_id: c for c in AGENT_CLASSES}
BY_AGENT_ID: dict[str, type[WellnessAgentBase]] = {c.agent_id: c for c in AGENT_CLASSES}


def get_agent(key: str) -> WellnessAgentBase:
    cls = REGISTRY.get(key) or BY_AGENT_ID.get(key)
    if cls is None:
        raise KeyError(f"unknown agent {key}")
    return cls()


def active_agent_ids(db: Session) -> list[str]:
    return [a.agent_id for a in db.scalars(select(WellnessAgent).where(WellnessAgent.status == "active"))]
