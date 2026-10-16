"""Read-only queries for the staff user list and usage statistics."""

import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import utcnow
from app.db_models import (
    Cohort,
    CohortMember,
    EngageProgress,
    PromptHistory,
    PromptUsage,
    Role,
    User,
)


@dataclass(frozen=True, slots=True)
class Overview:
    """Headline usage numbers."""

    users: int
    users_with_access: int
    prompts_today: int
    prompts_by_day: list[tuple[date, int]]
    prompts_by_feature: dict[str, int]
    engage_solved_by_level: dict[int, int]


async def list_users(
    session: AsyncSession,
    *,
    emails: Select[str] | None,
    search: str | None,
    role: Role | None,
    today: date,
    limit: int,
    offset: int,
) -> tuple[list[tuple[User, int]], int]:
    """Return users (optionally limited to a set of addresses) with today's prompt count."""
    prompts = (
        select(PromptUsage.count)
        .where(PromptUsage.user_id == User.id, PromptUsage.day == today)
        .scalar_subquery()
    )
    conditions = []
    if search:
        conditions.append(User.email.contains(search.lower(), autoescape=True))
    if role:
        conditions.append(User.role == role)
    if emails is not None:
        conditions.append(User.email.in_(emails))
    query = select(User, func.coalesce(prompts, 0)).where(*conditions)
    rows = await session.execute(query.order_by(User.created_at.desc()).limit(limit).offset(offset))
    total = await session.scalar(select(func.count(User.id)).where(*conditions))
    return [(user, count) for user, count in rows], total or 0


def cohort_emails(cohort_id: uuid.UUID) -> Select[str]:
    """Subquery: active addresses of one cohort."""
    return select(CohortMember.email).where(
        CohortMember.cohort_id == cohort_id, CohortMember.revoked_at.is_(None)
    )


async def overview(
    session: AsyncSession, *, emails: Select[str] | None, today: date, since: date
) -> Overview:
    """Compute headline numbers for the stats page."""
    user_ids = select(User.id)
    if emails is not None:
        user_ids = user_ids.where(User.email.in_(emails))

    now = utcnow()
    with_access = (
        select(func.count(func.distinct(CohortMember.email)))
        .join(Cohort, Cohort.id == CohortMember.cohort_id)
        .join(User, User.email == CohortMember.email)
        .where(
            CohortMember.revoked_at.is_(None),
            Cohort.starts_at <= now,
            Cohort.ends_at > now,
            User.id.in_(user_ids),
        )
    )
    by_day = await session.execute(
        select(PromptUsage.day, func.sum(PromptUsage.count))
        .where(PromptUsage.day >= since, PromptUsage.user_id.in_(user_ids))
        .group_by(PromptUsage.day)
        .order_by(PromptUsage.day)
    )
    by_feature = await session.execute(
        select(PromptHistory.feature, func.count(PromptHistory.id))
        .where(func.date(PromptHistory.created_at) >= since, PromptHistory.user_id.in_(user_ids))
        .group_by(PromptHistory.feature)
    )
    engage = await session.execute(
        select(EngageProgress.level, func.count())
        .where(EngageProgress.user_id.in_(user_ids))
        .group_by(EngageProgress.level)
    )
    prompts_by_day = [(day, int(total)) for day, total in by_day]
    return Overview(
        users=await session.scalar(select(func.count()).select_from(user_ids.subquery())) or 0,
        users_with_access=await session.scalar(with_access) or 0,
        prompts_today=next((t for d, t in prompts_by_day if d == today), 0),
        prompts_by_day=prompts_by_day,
        prompts_by_feature={str(f): int(n) for f, n in by_feature},
        engage_solved_by_level={int(level): int(n) for level, n in engage},
    )
