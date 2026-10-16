"""Data access operations for access requests."""

import uuid

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db_models import AccessRequest, AccessRequestStatus


async def has_pending(session: AsyncSession, user_id: uuid.UUID) -> bool:
    """Whether the user has a request awaiting review."""
    return bool(
        await session.scalar(
            select(
                exists().where(
                    AccessRequest.user_id == user_id,
                    AccessRequest.status == AccessRequestStatus.PENDING,
                )
            )
        )
    )
