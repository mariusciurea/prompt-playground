"""Data access operations for cohorts and their members."""

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.database.base import utcnow
from app.db_models import Cohort, CohortMember, User


async def list_with_counts(
    session: AsyncSession, *, owner_id: uuid.UUID | None = None, cohort_id: uuid.UUID | None = None
) -> list[tuple[Cohort, str | None, int]]:
    """Return cohorts with owner e-mail and active member count, optionally filtered."""
    owner = aliased(User)
    members = (
        select(func.count(CohortMember.id))
        .where(CohortMember.cohort_id == Cohort.id, CohortMember.revoked_at.is_(None))
        .scalar_subquery()
    )
    query = (
        select(Cohort, owner.email, members)
        .outerjoin(owner, owner.id == Cohort.owner_id)
        .order_by(Cohort.starts_at.desc())
    )
    if owner_id is not None:
        query = query.where(Cohort.owner_id == owner_id)
    if cohort_id is not None:
        query = query.where(Cohort.id == cohort_id)
    return [(c, email, count) for c, email, count in await session.execute(query)]


async def get(session: AsyncSession, cohort_id: uuid.UUID) -> Cohort | None:
    """Return a cohort by ID."""
    return await session.get(Cohort, cohort_id)


async def get_by_name(session: AsyncSession, name: str) -> Cohort | None:
    """Return a cohort by name."""
    return await session.scalar(select(Cohort).where(Cohort.name == name))


async def create(
    session: AsyncSession,
    *,
    name: str,
    starts_at: datetime,
    ends_at: datetime,
    owner_id: uuid.UUID | None,
) -> Cohort:
    """Add a cohort."""
    cohort = Cohort(name=name, starts_at=starts_at, ends_at=ends_at, owner_id=owner_id)
    session.add(cohort)
    await session.flush()
    return cohort


async def list_members(
    session: AsyncSession, cohort_id: uuid.UUID, *, search: str | None, limit: int, offset: int
) -> tuple[list[tuple[CohortMember, bool]], int]:
    """Return members with a flag telling whether they registered, plus the total."""
    conditions = [CohortMember.cohort_id == cohort_id]
    if search:
        conditions.append(CohortMember.email.contains(search.lower(), autoescape=True))
    registered = (
        select(User.id)
        .where(User.email == CohortMember.email, User.email_verified_at.is_not(None))
        .exists()
    )
    rows = await session.execute(
        select(CohortMember, registered)
        .where(*conditions)
        .order_by(CohortMember.email)
        .limit(limit)
        .offset(offset)
    )
    total = await session.scalar(select(func.count(CohortMember.id)).where(*conditions))
    return [(member, bool(is_registered)) for member, is_registered in rows], total or 0


async def members_by_email(
    session: AsyncSession, cohort_id: uuid.UUID, emails: Sequence[str]
) -> dict[str, CohortMember]:
    """Return existing memberships for the given addresses."""
    rows = await session.scalars(
        select(CohortMember).where(
            CohortMember.cohort_id == cohort_id, CohortMember.email.in_(emails)
        )
    )
    return {member.email: member for member in rows}


def add_member(
    session: AsyncSession, cohort_id: uuid.UUID, email: str, added_by: uuid.UUID
) -> CohortMember:
    """Add a membership to the session."""
    member = CohortMember(cohort_id=cohort_id, email=email, added_by=added_by)
    session.add(member)
    return member


async def get_member(
    session: AsyncSession, cohort_id: uuid.UUID, email: str
) -> CohortMember | None:
    """Return one membership."""
    return await session.scalar(
        select(CohortMember).where(CohortMember.cohort_id == cohort_id, CohortMember.email == email)
    )


async def verified_emails(session: AsyncSession, emails: Sequence[str]) -> set[str]:
    """Return which of the addresses belong to verified accounts."""
    rows = await session.scalars(
        select(User.email).where(User.email.in_(emails), User.email_verified_at.is_not(None))
    )
    return set(rows)


def owned_member_emails(owner_id: uuid.UUID) -> Select[str]:
    """Subquery: addresses in cohorts owned by an instructor."""
    return (
        select(CohortMember.email)
        .join(Cohort, Cohort.id == CohortMember.cohort_id)
        .where(Cohort.owner_id == owner_id)
    )


def is_active(cohort: Cohort) -> bool:
    """Whether the cohort grants access right now."""
    now = utcnow()
    return cohort.starts_at <= now < cohort.ends_at
