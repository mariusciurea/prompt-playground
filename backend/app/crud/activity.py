"""Data access for Engage progress, prompt history, and custom skills."""

import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import utcnow
from app.db_models import CustomSkill, EngageProgress, Feature, PromptHistory


async def solved_levels(session: AsyncSession, user_id: uuid.UUID) -> set[int]:
    """Return the levels a user has solved."""
    rows = await session.scalars(
        select(EngageProgress.level).where(EngageProgress.user_id == user_id)
    )
    return set(rows)


async def mark_solved(session: AsyncSession, user_id: uuid.UUID, level: int) -> None:
    """Record that a user solved a level (idempotent)."""
    stmt = (
        insert(EngageProgress)
        .values(user_id=user_id, level=level, solved_at=utcnow())
        .on_conflict_do_nothing(index_elements=[EngageProgress.user_id, EngageProgress.level])
    )
    await session.execute(stmt)
    await session.commit()


async def list_history(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    feature: Feature | None,
    limit: int,
    offset: int,
) -> tuple[list[PromptHistory], int]:
    """Return a user's history, newest first."""
    conditions = [PromptHistory.user_id == user_id]
    if feature is not None:
        conditions.append(PromptHistory.feature == feature)
    rows = await session.scalars(
        select(PromptHistory)
        .where(*conditions)
        .order_by(PromptHistory.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    total = await session.scalar(select(func.count(PromptHistory.id)).where(*conditions))
    return list(rows), total or 0


async def clear_history(session: AsyncSession, user_id: uuid.UUID) -> None:
    """Delete all of a user's history."""
    await session.execute(delete(PromptHistory).where(PromptHistory.user_id == user_id))
    await session.commit()


async def list_custom_skills(session: AsyncSession, user_id: uuid.UUID) -> list[CustomSkill]:
    """Return a user's private skills, newest first."""
    rows = await session.scalars(
        select(CustomSkill)
        .where(CustomSkill.user_id == user_id)
        .order_by(CustomSkill.created_at.desc())
    )
    return list(rows)


async def count_custom_skills(session: AsyncSession, user_id: uuid.UUID) -> int:
    """Count a user's private skills."""
    return (
        await session.scalar(
            select(func.count(CustomSkill.id)).where(CustomSkill.user_id == user_id)
        )
        or 0
    )


async def get_custom_skill(
    session: AsyncSession, user_id: uuid.UUID, skill_id: uuid.UUID
) -> CustomSkill | None:
    """Return one of a user's skills."""
    skill = await session.get(CustomSkill, skill_id)
    return skill if skill is not None and skill.user_id == user_id else None
