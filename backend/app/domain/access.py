"""Course access rules: who may use the LLM features right now."""

import json
from dataclasses import asdict, dataclass
from datetime import datetime

from sqlalchemy import ColumnElement, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.store import Store
from app.database.base import utcnow
from app.db_models import Cohort, CohortMember, Role, User

_CACHE_TTL = 60
_GENERATION_KEY = "access:generation"


@dataclass(frozen=True, slots=True)
class ActiveCohort:
    """A cohort that currently grants access."""

    name: str
    ends_at: datetime


@dataclass(frozen=True, slots=True)
class AccessStatus:
    """Whether a user has access, and through which cohorts."""

    has_access: bool
    cohorts: tuple[ActiveCohort, ...] = ()


async def _query_active_cohorts(session: AsyncSession, user: User) -> tuple[ActiveCohort, ...]:
    now = utcnow()
    member_of = select(CohortMember.cohort_id).where(
        CohortMember.email == user.email, CohortMember.revoked_at.is_(None)
    )
    conditions: list[ColumnElement[bool]] = [Cohort.id.in_(member_of)]
    if user.role is Role.INSTRUCTOR:
        conditions.append(Cohort.owner_id == user.id)
    rows = await session.execute(
        select(Cohort.name, Cohort.ends_at)
        .where(or_(*conditions), Cohort.starts_at <= now, Cohort.ends_at > now)
        .order_by(Cohort.ends_at)
    )
    return tuple(ActiveCohort(name, ends_at) for name, ends_at in rows)


async def get_access(session: AsyncSession, store: Store, user: User) -> AccessStatus:
    """Return the user's access, cached briefly and never past the earliest cohort end."""
    if user.role is Role.ADMIN:
        return AccessStatus(has_access=True)

    generation = await store.get(_GENERATION_KEY) or "0"
    key = f"access:{generation}:{user.id}"
    if cached := await store.get(key):
        data = json.loads(cached)
        cohorts = tuple(
            ActiveCohort(c["name"], datetime.fromisoformat(c["ends_at"])) for c in data["cohorts"]
        )
        if all(c.ends_at > utcnow() for c in cohorts):
            return AccessStatus(has_access=data["has_access"], cohorts=cohorts)

    cohorts = await _query_active_cohorts(session, user)
    status = AccessStatus(has_access=bool(cohorts), cohorts=cohorts)
    ttl = _CACHE_TTL
    if cohorts:
        ttl = max(1, min(ttl, int((cohorts[0].ends_at - utcnow()).total_seconds())))
    payload = {
        "has_access": status.has_access,
        "cohorts": [{**asdict(c), "ends_at": c.ends_at.isoformat()} for c in cohorts],
    }
    await store.set(key, json.dumps(payload), ttl)
    return status


async def invalidate_access_cache(store: Store) -> None:
    """Drop every cached access decision (call after any cohort or membership change)."""
    await store.incr(_GENERATION_KEY, 30 * 86400)
