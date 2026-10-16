"""Daily prompt quota: atomic reservation, refunds, and status."""

import uuid
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import QuotaExceededError
from app.core.settings import Settings
from app.database.base import utcnow
from app.db_models import PromptUsage, Role, User


@dataclass(frozen=True, slots=True)
class QuotaStatus:
    """Today's usage; `limit` and `remaining` are None for exempt users."""

    used: int
    limit: int | None
    remaining: int | None
    resets_at: datetime


def is_exempt(user: User, settings: Settings) -> bool:
    """Admins (and, if configured, instructors) have no daily limit."""
    return user.role is Role.ADMIN or (
        user.role is Role.INSTRUCTOR and settings.instructors_exempt_from_quota
    )


def quota_day(settings: Settings, now: datetime | None = None) -> date:
    """Return the quota day in the configured time zone."""
    return (now or utcnow()).astimezone(settings.quota_zone).date()


def next_reset(settings: Settings, now: datetime | None = None) -> datetime:
    """Return when the current quota day ends."""
    tomorrow = quota_day(settings, now) + timedelta(days=1)
    return datetime.combine(tomorrow, time.min, tzinfo=settings.quota_zone)


def _status(user: User, used: int, settings: Settings) -> QuotaStatus:
    limit = None if is_exempt(user, settings) else settings.daily_prompt_limit
    return QuotaStatus(
        used=used,
        limit=limit,
        remaining=None if limit is None else max(limit - used, 0),
        resets_at=next_reset(settings),
    )


async def get_status(session: AsyncSession, user: User, settings: Settings) -> QuotaStatus:
    """Return today's usage for a user."""
    used = await session.scalar(
        select(PromptUsage.count).where(
            PromptUsage.user_id == user.id, PromptUsage.day == quota_day(settings)
        )
    )
    return _status(user, used or 0, settings)


async def reserve(
    session: AsyncSession, user: User, settings: Settings
) -> tuple[date, QuotaStatus]:
    """Atomically count one prompt; raise QuotaExceededError if the limit is reached.

    Returns the quota day (needed for a refund) and the updated status.
    """
    day = quota_day(settings)
    stmt = insert(PromptUsage).values(user_id=user.id, day=day, count=1)
    upsert = stmt.on_conflict_do_update(
        index_elements=[PromptUsage.user_id, PromptUsage.day],
        set_={"count": PromptUsage.count + 1},
        where=None
        if is_exempt(user, settings)
        else PromptUsage.count < settings.daily_prompt_limit,
    ).returning(PromptUsage.count)
    used = await session.scalar(upsert)
    await session.commit()
    if used is None:
        raise QuotaExceededError(
            f"You've used all {settings.daily_prompt_limit} prompts for today. "
            "Your quota resets at midnight (Romania time)."
        )
    return day, _status(user, used, settings)


async def refund(session: AsyncSession, user_id: uuid.UUID, day: date) -> None:
    """Give back a prompt that failed for reasons outside the user's control."""
    await session.execute(
        update(PromptUsage)
        .where(PromptUsage.user_id == user_id, PromptUsage.day == day, PromptUsage.count > 0)
        .values(count=PromptUsage.count - 1)
    )
    await session.commit()
