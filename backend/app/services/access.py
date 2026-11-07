"""Consent-based access control for coaches and counsellors.

Rules:
* An individual always sees their own data.
* A coach/counsellor sees an individual's data only with an *active*,
  unexpired AccessGrant from that individual covering the requested scope.
* Administrators do NOT get automatic access to individual wellness data;
  they only see anonymised aggregates with a minimum group size.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import AccessGrant, User
from .audit import audit

SCOPES = ("assessments", "interviews", "reports", "observations")


def active_grant(db: Session, user_id: uuid.UUID, grantee_id: uuid.UUID, scope: str) -> AccessGrant | None:
    now = datetime.now(timezone.utc)
    grants = db.scalars(
        select(AccessGrant).where(
            AccessGrant.user_id == user_id,
            AccessGrant.grantee_id == grantee_id,
            AccessGrant.status == "active",
        )
    ).all()
    for g in grants:
        if scope in g.scopes and (g.expires_at is None or g.expires_at > now):
            return g
    return None


def ensure_can_view(db: Session, actor: User, subject_id: uuid.UUID, scope: str) -> None:
    if actor.user_id == subject_id:
        return
    if actor.user_role in ("coach", "counselor") and active_grant(db, subject_id, actor.user_id, scope):
        audit(db, actor.user_id, "view_individual_data", subject_id, scope)
        return
    audit(db, actor.user_id, "access_denied", subject_id, scope)
    db.commit()
    raise HTTPException(
        status.HTTP_403_FORBIDDEN,
        "You do not have the individual's consent to access this information.",
    )


def resolve_subject(db: Session, actor: User, user_id: uuid.UUID | None, scope: str) -> uuid.UUID:
    subject = user_id or actor.user_id
    ensure_can_view(db, actor, subject, scope)
    return subject
