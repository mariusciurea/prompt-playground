"""Usage statistics endpoint."""

import uuid
from datetime import timedelta

from fastapi import APIRouter
from sqlalchemy import Select

from app.core.state import StateDep
from app.crud import stats
from app.crud.cohorts import owned_member_emails
from app.data_models.admin import DailyCount, StatsOut
from app.database.session import SessionDep
from app.domain import staff
from app.domain.quota import quota_day
from app.routers.admin.deps import ActorDep

router = APIRouter(prefix="/stats")


@router.get("")
async def overview(
    actor: ActorDep, session: SessionDep, state: StateDep, cohort_id: uuid.UUID | None = None
) -> StatsOut:
    """Usage over the last 14 days, for everyone or for one cohort."""
    emails: Select[str] | None = None
    if cohort_id is not None:
        await staff.get_managed_cohort(session, actor, cohort_id)
        emails = stats.cohort_emails(cohort_id)
    elif not actor.is_admin:
        emails = owned_member_emails(actor.user.id)
    today = quota_day(state.settings)
    data = await stats.overview(session, emails=emails, today=today, since=today - timedelta(13))
    return StatsOut(
        users=data.users,
        users_with_access=data.users_with_access,
        prompts_today=data.prompts_today,
        prompts_by_day=[DailyCount(day=d, count=c) for d, c in data.prompts_by_day],
        prompts_by_feature=data.prompts_by_feature,
        engage_solved_by_level=data.engage_solved_by_level,
    )
