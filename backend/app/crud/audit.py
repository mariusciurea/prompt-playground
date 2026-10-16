"""Data access operations for the audit log."""

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db_models import AuditLog, User


def record(
    session: AsyncSession,
    *,
    actor_id: uuid.UUID | None,
    action: str,
    target: str | None = None,
    details: dict[str, Any] | None = None,
    ip: str | None = None,
) -> None:
    """Add an audit entry; it is saved with the caller's commit."""
    session.add(
        AuditLog(actor_id=actor_id, action=action, target=target, details=details or {}, ip=ip)
    )


async def list_entries(
    session: AsyncSession, *, action: str | None, limit: int, offset: int
) -> tuple[list[tuple[AuditLog, str | None]], int]:
    """Return newest entries first with the actor's e-mail, and the total count."""
    query = select(AuditLog, User.email).outerjoin(User, User.id == AuditLog.actor_id)
    count = select(func.count(AuditLog.id))
    if action:
        query = query.where(AuditLog.action == action)
        count = count.where(AuditLog.action == action)
    rows = await session.execute(
        query.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
    )
    return [(entry, email) for entry, email in rows], await session.scalar(count) or 0
