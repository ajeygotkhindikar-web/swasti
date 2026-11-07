"""SAMPURNA relational data model (PostgreSQL).

All tables use UUID primary keys (except small master-data lookups that
are referenced by stable codes), foreign keys with explicit ON DELETE rules,
created/updated timestamps and indexes on the common access paths.
Assessment history is append-only: a new quarterly assessment creates new
rows and never overwrites earlier results.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


ROLES = ("individual", "coach", "counselor", "admin")


# ---------------------------------------------------------------- users
class User(TimestampMixin, Base):
    __tablename__ = "users"
    user_id: Mapped[uuid.UUID] = uuid_pk()
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    phone_number: Mapped[str | None] = mapped_column(String(30))
    occupation: Mapped[str | None] = mapped_column(String(120))
    industry: Mapped[str | None] = mapped_column(String(120))
    age_group: Mapped[str | None] = mapped_column(String(20))
    city: Mapped[str | None] = mapped_column(String(120))
    registration_date: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)
    user_role: Mapped[str] = mapped_column(String(20), default="individual", nullable=False)
    account_status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint("user_role in ('individual','coach','counselor','admin')", name="ck_users_role"),
        CheckConstraint("account_status in ('active','suspended','deleted')", name="ck_users_status"),
        Index("ix_users_role", "user_role"),
    )


class UserPreference(TimestampMixin, Base):
    __tablename__ = "user_preferences"
    preference_id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, unique=True
    )
    theme: Mapped[str] = mapped_column(String(10), default="system")
    language: Mapped[str] = mapped_column(String(10), default="en")
    reminders_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    push_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    category_weights: Mapped[dict | None] = mapped_column(JSON)  # optional personal weights


# ---------------------------------------------------------------- master data
class WellnessCategory(TimestampMixin, Base):
    __tablename__ = "wellness_categories"
    category_id: Mapped[str] = mapped_column(String(10), primary_key=True)  # e.g. MEN
    category_name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    category_description: Mapped[str] = mapped_column(Text, nullable=False)
    category_icon: Mapped[str] = mapped_column(String(50), nullable=False)
    default_weightage: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    target_score: Mapped[float] = mapped_column(Float, default=75.0, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)
    agent_code: Mapped[str] = mapped_column(String(60), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    parameters: Mapped[list["WellnessParameter"]] = relationship(
        back_populates="category", order_by="WellnessParameter.display_order"
    )
    __table_args__ = (
        CheckConstraint("default_weightage >= 0", name="ck_cat_weight"),
        CheckConstraint("target_score between 0 and 100", name="ck_cat_target"),
    )


class WellnessParameter(TimestampMixin, Base):
    __tablename__ = "wellness_parameters"
    parameter_id: Mapped[str] = mapped_column(String(20), primary_key=True)  # e.g. MEN_01
    category_id: Mapped[str] = mapped_column(
        ForeignKey("wellness_categories.category_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    parameter_name: Mapped[str] = mapped_column(String(120), nullable=False)
    parameter_description: Mapped[str] = mapped_column(Text, nullable=False)  # the question text
    response_type: Mapped[str] = mapped_column(String(20), nullable=False)
    options: Mapped[list] = mapped_column(JSON, nullable=False)  # [{value, label}]
    scoring_rule: Mapped[dict] = mapped_column(JSON, nullable=False)  # {"reverse": bool}
    parameter_weightage: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    allow_not_applicable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    category: Mapped[WellnessCategory] = relationship(back_populates="parameters")
    __table_args__ = (
        CheckConstraint(
            "response_type in ('likert','frequency','yes_no','range')", name="ck_param_type"
        ),
        CheckConstraint("parameter_weightage > 0", name="ck_param_weight"),
    )


class ScientificReference(TimestampMixin, Base):
    __tablename__ = "scientific_references"
    reference_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    category_id: Mapped[str | None] = mapped_column(
        ForeignKey("wellness_categories.category_id", ondelete="RESTRICT"), index=True
    )
    reference_title: Mapped[str] = mapped_column(String(300), nullable=False)
    issuing_organization: Mapped[str] = mapped_column(String(200), nullable=False)
    reference_url: Mapped[str] = mapped_column(String(500), nullable=False)
    publication_date: Mapped[str | None] = mapped_column(String(20))
    last_verified_date: Mapped[date | None] = mapped_column(Date)
    verification_status: Mapped[str] = mapped_column(String(30), default="pending_verification")
    evidence_level: Mapped[str] = mapped_column(String(40), nullable=False)
    supporting_evidence: Mapped[str] = mapped_column(Text, nullable=False)


class WellnessAgent(TimestampMixin, Base):
    __tablename__ = "wellness_agents"
    agent_id: Mapped[str] = mapped_column(String(60), primary_key=True)
    category_id: Mapped[str] = mapped_column(
        ForeignKey("wellness_categories.category_id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    agent_name: Mapped[str] = mapped_column(String(120), nullable=False)
    agent_description: Mapped[str] = mapped_column(Text, nullable=False)
    agent_version: Mapped[str] = mapped_column(String(20), nullable=False)
    execution_mode: Mapped[str] = mapped_column(String(20), default="parallel")  # parallel|sequential
    status: Mapped[str] = mapped_column(String(20), default="active")  # active|disabled


class WellnessRecommendation(TimestampMixin, Base):
    __tablename__ = "wellness_recommendations"
    recommendation_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    category_id: Mapped[str] = mapped_column(
        ForeignKey("wellness_categories.category_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    agent_id: Mapped[str] = mapped_column(
        ForeignKey("wellness_agents.agent_id", ondelete="RESTRICT"), nullable=False
    )
    recommendation_title: Mapped[str] = mapped_column(String(200), nullable=False)
    recommendation_description: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_action: Mapped[str] = mapped_column(Text, nullable=False)
    micro_habit: Mapped[str] = mapped_column(String(200), nullable=False)
    suggested_frequency: Mapped[str] = mapped_column(String(20), nullable=False)  # daily|weekly
    evidence_reference: Mapped[str] = mapped_column(
        ForeignKey("scientific_references.reference_id", ondelete="RESTRICT"), nullable=False
    )
    target_parameters: Mapped[list] = mapped_column(JSON, default=list)  # parameter ids addressed
    recommendation_priority: Mapped[int] = mapped_column(Integer, default=2)  # 1 high .. 3 low
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class SystemSetting(TimestampMixin, Base):
    """Configurable scoring thresholds and other admin settings."""
    __tablename__ = "system_settings"
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


# ---------------------------------------------------------------- assessments
class AssessmentSession(TimestampMixin, Base):
    __tablename__ = "assessment_sessions"
    assessment_id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False
    )
    assessment_type: Mapped[str] = mapped_column(String(20), default="quarterly")  # baseline|quarterly|adhoc
    assessment_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    assessment_period: Mapped[str] = mapped_column(String(10), nullable=False)  # e.g. 2026-Q4
    completion_status: Mapped[str] = mapped_column(String(20), default="in_progress")
    assessment_source: Mapped[str] = mapped_column(String(20), default="self")
    interviewer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.user_id", ondelete="SET NULL")
    )
    overall_indicator: Mapped[float | None] = mapped_column(Float)
    coverage: Mapped[float | None] = mapped_column(Float)
    agents_status: Mapped[str] = mapped_column(String(20), default="pending")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    responses: Mapped[list["AssessmentResponse"]] = relationship(back_populates="session")
    __table_args__ = (
        CheckConstraint("assessment_source in ('self','interview')", name="ck_assess_source"),
        CheckConstraint(
            "completion_status in ('in_progress','completed','abandoned')", name="ck_assess_status"
        ),
        Index("ix_assess_user_date", "user_id", "assessment_date"),
    )


class AssessmentResponse(TimestampMixin, Base):
    __tablename__ = "assessment_responses"
    response_id: Mapped[uuid.UUID] = uuid_pk()
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assessment_sessions.assessment_id", ondelete="CASCADE"), nullable=False
    )
    parameter_id: Mapped[str] = mapped_column(
        ForeignKey("wellness_parameters.parameter_id", ondelete="RESTRICT"), nullable=False
    )
    response_value: Mapped[int | None] = mapped_column(Integer)  # 1..5 or null
    response_status: Mapped[str] = mapped_column(String(20), default="answered")
    normalized_score: Mapped[float | None] = mapped_column(Float)
    comments: Mapped[str | None] = mapped_column(Text)
    response_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    session: Mapped[AssessmentSession] = relationship(back_populates="responses")
    __table_args__ = (
        UniqueConstraint("assessment_id", "parameter_id", name="uq_response_param"),
        CheckConstraint(
            "response_status in ('answered','not_applicable','prefer_not_to_answer')",
            name="ck_resp_status",
        ),
        CheckConstraint(
            "(response_status = 'answered' and response_value between 1 and 5) or "
            "(response_status <> 'answered' and response_value is null)",
            name="ck_resp_value",
        ),
    )


class CategoryComment(TimestampMixin, Base):
    __tablename__ = "assessment_category_comments"
    comment_id: Mapped[uuid.UUID] = uuid_pk()
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assessment_sessions.assessment_id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_id: Mapped[str] = mapped_column(
        ForeignKey("wellness_categories.category_id", ondelete="RESTRICT"), nullable=False
    )
    comment: Mapped[str] = mapped_column(Text, nullable=False)


class WellnessCategoryScore(TimestampMixin, Base):
    __tablename__ = "wellness_category_scores"
    category_score_id: Mapped[uuid.UUID] = uuid_pk()
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assessment_sessions.assessment_id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False
    )
    category_id: Mapped[str] = mapped_column(
        ForeignKey("wellness_categories.category_id", ondelete="RESTRICT"), nullable=False
    )
    calculated_score: Mapped[float | None] = mapped_column(Float)  # null = insufficient data
    wellness_level: Mapped[str] = mapped_column(String(30), nullable=False)
    target_score: Mapped[float] = mapped_column(Float, nullable=False)
    score_gap: Mapped[float | None] = mapped_column(Float)
    coverage: Mapped[float] = mapped_column(Float, nullable=False)
    answered_count: Mapped[int] = mapped_column(Integer, nullable=False)
    calculated_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (
        UniqueConstraint("assessment_id", "category_id", name="uq_cat_score"),
        Index("ix_catscore_user_cat", "user_id", "category_id"),
    )


# ---------------------------------------------------------------- agents
class AgentAssessment(TimestampMixin, Base):
    __tablename__ = "agent_assessments"
    agent_assessment_id: Mapped[uuid.UUID] = uuid_pk()
    agent_id: Mapped[str] = mapped_column(
        ForeignKey("wellness_agents.agent_id", ondelete="RESTRICT"), nullable=False
    )
    agent_version: Mapped[str] = mapped_column(String(20), nullable=False)
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assessment_sessions.assessment_id", ondelete="CASCADE"), nullable=False
    )
    category_score_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("wellness_category_scores.category_score_id", ondelete="CASCADE"), nullable=False
    )
    analysis_summary: Mapped[str] = mapped_column(Text, nullable=False)
    identified_gaps: Mapped[list] = mapped_column(JSON, default=list)
    recommendation_summary: Mapped[str] = mapped_column(Text, nullable=False)
    output: Mapped[dict] = mapped_column(JSON, nullable=False)  # full structured agent JSON
    confidence_level: Mapped[str] = mapped_column(String(10), nullable=False)
    execution_status: Mapped[str] = mapped_column(String(20), nullable=False)
    execution_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (
        UniqueConstraint("assessment_id", "agent_id", "agent_version", name="uq_agent_assessment"),
        Index("ix_agent_assess_assessment", "assessment_id"),
    )


class AgentExecutionLog(Base):
    __tablename__ = "agent_execution_logs"
    log_id: Mapped[uuid.UUID] = uuid_pk()
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    agent_id: Mapped[str] = mapped_column(
        ForeignKey("wellness_agents.agent_id", ondelete="RESTRICT"), nullable=False
    )
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assessment_sessions.assessment_id", ondelete="CASCADE"), nullable=False, index=True
    )
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # running|succeeded|failed
    error_message: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CrossWellnessInsight(TimestampMixin, Base):
    __tablename__ = "cross_wellness_insights"
    insight_id: Mapped[uuid.UUID] = uuid_pk()
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assessment_sessions.assessment_id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False)
    categories: Mapped[list] = mapped_column(JSON, nullable=False)
    insight_type: Mapped[str] = mapped_column(String(30), nullable=False)  # co_low|co_decline
    message: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict] = mapped_column(JSON, nullable=False)  # the actual data points used


# ---------------------------------------------------------------- plans & habits
class UserWellnessPlan(TimestampMixin, Base):
    __tablename__ = "user_wellness_plans"
    plan_id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    category_id: Mapped[str] = mapped_column(ForeignKey("wellness_categories.category_id", ondelete="RESTRICT"), nullable=False)
    recommendation_id: Mapped[str] = mapped_column(
        ForeignKey("wellness_recommendations.recommendation_id", ondelete="RESTRICT"), nullable=False
    )
    start_date: Mapped[date] = mapped_column(Date, default=date.today)
    target_date: Mapped[date | None] = mapped_column(Date)
    completion_status: Mapped[str] = mapped_column(String(20), default="active")
    user_feedback: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (UniqueConstraint("user_id", "recommendation_id", name="uq_plan_rec"),)


class MicroHabit(TimestampMixin, Base):
    __tablename__ = "micro_habit_tracking"
    habit_id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    category_id: Mapped[str] = mapped_column(ForeignKey("wellness_categories.category_id", ondelete="RESTRICT"), nullable=False)
    recommendation_id: Mapped[str | None] = mapped_column(
        ForeignKey("wellness_recommendations.recommendation_id", ondelete="SET NULL")
    )
    habit_name: Mapped[str] = mapped_column(String(200), nullable=False)
    frequency: Mapped[str] = mapped_column(String(20), nullable=False)  # daily|weekly
    target_frequency: Mapped[int] = mapped_column(Integer, nullable=False)  # times per period
    completion_count: Mapped[int] = mapped_column(Integer, default=0)
    reminder_time: Mapped[str | None] = mapped_column(String(5))  # HH:MM
    start_date: Mapped[date] = mapped_column(Date, default=date.today)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active|paused|archived
    user_feedback: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (CheckConstraint("target_frequency between 1 and 14", name="ck_habit_target"),)


class HabitLog(Base):
    __tablename__ = "habit_logs"
    log_id: Mapped[uuid.UUID] = uuid_pk()
    habit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("micro_habit_tracking.habit_id", ondelete="CASCADE"), nullable=False
    )
    log_date: Mapped[date] = mapped_column(Date, nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (UniqueConstraint("habit_id", "log_date", name="uq_habit_day"),)


# ---------------------------------------------------------------- reviews & interviews
class QuarterlyReview(TimestampMixin, Base):
    __tablename__ = "quarterly_reviews"
    review_id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False, index=True)
    quarter: Mapped[int] = mapped_column(Integer, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_assessment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("assessment_sessions.assessment_id", ondelete="RESTRICT")
    )
    current_assessment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assessment_sessions.assessment_id", ondelete="RESTRICT"), nullable=False
    )
    overall_progress: Mapped[float | None] = mapped_column(Float)
    comparison: Mapped[dict] = mapped_column(JSON, nullable=False)
    review_summary: Mapped[str] = mapped_column(Text, nullable=False)
    coach_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.user_id", ondelete="SET NULL"))
    coach_notes: Mapped[str | None] = mapped_column(Text)
    review_date: Mapped[date] = mapped_column(Date, default=date.today)
    __table_args__ = (
        CheckConstraint("quarter between 1 and 4", name="ck_review_quarter"),
        UniqueConstraint("current_assessment_id", name="uq_review_current"),
    )


class InterviewRecord(TimestampMixin, Base):
    __tablename__ = "interview_records"
    interview_id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False, index=True)
    interviewer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False, index=True)
    assessment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("assessment_sessions.assessment_id", ondelete="SET NULL")
    )
    interview_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="completed")  # scheduled|completed|cancelled
    observations: Mapped[dict | None] = mapped_column(JSON)  # {category_id: note}
    interview_summary: Mapped[str | None] = mapped_column(Text)
    summary_source: Mapped[str | None] = mapped_column(String(20))  # interviewer|ai_draft
    transcription_reference: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("interview_transcripts.transcript_id", ondelete="SET NULL")
    )
    consent_status: Mapped[str] = mapped_column(String(20), default="not_requested")
    follow_up_plan: Mapped[str | None] = mapped_column(Text)
    follow_up_date: Mapped[date | None] = mapped_column(Date)


class InterviewTranscript(Base):
    """Separately secured storage: transcript text is encrypted at rest (Fernet)."""
    __tablename__ = "interview_transcripts"
    transcript_id: Mapped[uuid.UUID] = uuid_pk()
    owner_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ProfessionalObservation(TimestampMixin, Base):
    __tablename__ = "professional_observations"
    observation_id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False, index=True)
    counselor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False)
    category_id: Mapped[str | None] = mapped_column(ForeignKey("wellness_categories.category_id"))
    observation: Mapped[str] = mapped_column(Text, nullable=False)
    referral_recommended: Mapped[bool] = mapped_column(Boolean, default=False)
    referral_note: Mapped[str | None] = mapped_column(Text)
    follow_up_date: Mapped[date | None] = mapped_column(Date)


# ---------------------------------------------------------------- consent, access, audit
class ConsentRecord(Base):
    __tablename__ = "consent_and_privacy"
    consent_id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    consent_type: Mapped[str] = mapped_column(String(40), nullable=False)
    consent_version: Mapped[str] = mapped_column(String(10), nullable=False)
    granted_status: Mapped[bool] = mapped_column(Boolean, nullable=False)
    consent_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    withdrawal_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint(
            "consent_type in ('data_processing','ai_analysis','interview_transcription',"
            "'push_notifications','anonymized_research')",
            name="ck_consent_type",
        ),
    )


class AccessGrant(TimestampMixin, Base):
    """An individual's explicit approval for a named coach/counselor to see their data."""
    __tablename__ = "access_grants"
    grant_id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    grantee_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    scopes: Mapped[list] = mapped_column(JSON, nullable=False)  # assessments, interviews, reports, observations
    status: Mapped[str] = mapped_column(String(20), default="active")  # active|revoked
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (CheckConstraint("user_id <> grantee_id", name="ck_grant_not_self"),)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    audit_id: Mapped[uuid.UUID] = uuid_pk()
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.user_id", ondelete="SET NULL"), index=True)
    subject_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.user_id", ondelete="SET NULL"), index=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    resource: Mapped[str | None] = mapped_column(String(120))
    details: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class Notification(Base):
    __tablename__ = "notifications"
    notification_id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    notification_type: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    dedupe_key: Mapped[str | None] = mapped_column(String(120))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (UniqueConstraint("user_id", "dedupe_key", name="uq_notif_dedupe"),)
