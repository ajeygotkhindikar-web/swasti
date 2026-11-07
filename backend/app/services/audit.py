import uuid

from sqlalchemy.orm import Session

from ..models import AuditLog


def audit(
    db: Session,
    actor_id: uuid.UUID | None,
    action: str,
    subject_user_id: uuid.UUID | None = None,
    resource: str | None = None,
    details: dict | None = None,
) -> None:
    """Add an audit row to the current transaction (caller commits)."""
    db.add(
        AuditLog(
            actor_id=actor_id,
            subject_user_id=subject_user_id,
            action=action,
            resource=resource,
            details=details,
        )
    )
