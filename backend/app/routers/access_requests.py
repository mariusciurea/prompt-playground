"""Endpoints for users asking to be granted course access."""

from fastapi import APIRouter, status
from sqlalchemy import select

from app.auth.dependencies import CurrentUser
from app.core.exceptions import ConflictError, NotFoundError
from app.core.rate_limit import ACCESS_REQUEST_PER_USER
from app.core.state import StateDep
from app.data_models.admin import AccessRequestIn, MyAccessRequestOut
from app.database.session import SessionDep
from app.db_models import AccessRequest
from app.domain import staff
from app.domain.access import get_access

router = APIRouter(prefix="/access-requests", tags=["access requests"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def request_access(
    data: AccessRequestIn, user: CurrentUser, session: SessionDep, state: StateDep
) -> MyAccessRequestOut:
    """Ask staff for course access."""
    if (await get_access(session, state.store, user)).has_access:
        raise ConflictError("You already have access.")
    await state.rate_limiter.hit(ACCESS_REQUEST_PER_USER, str(user.id))
    request = await staff.create_access_request(session, user, data.message)
    return MyAccessRequestOut.model_validate(request)


@router.get("/mine")
async def my_latest_request(user: CurrentUser, session: SessionDep) -> MyAccessRequestOut:
    """Return the user's most recent request."""
    request = await session.scalar(
        select(AccessRequest)
        .where(AccessRequest.user_id == user.id)
        .order_by(AccessRequest.created_at.desc())
        .limit(1)
    )
    if request is None:
        raise NotFoundError("No request yet.")
    return MyAccessRequestOut.model_validate(request)
