"""Access request review endpoints."""

import uuid

from fastapi import APIRouter, BackgroundTasks
from sqlalchemy import func, select

from app.core.state import StateDep
from app.data_models.admin import AccessRequestOut, ReviewIn
from app.data_models.common import MessageOut, Page
from app.database.session import SessionDep
from app.db_models import AccessRequest, AccessRequestStatus, Cohort, User
from app.domain import staff
from app.domain.email import deliver
from app.routers.admin.deps import ActorDep
from app.routers.helpers import PaginationDep

router = APIRouter(prefix="/access-requests")


@router.get("")
async def list_requests(
    actor: ActorDep,
    session: SessionDep,
    page: PaginationDep,
    status: AccessRequestStatus = AccessRequestStatus.PENDING,
) -> Page[AccessRequestOut]:
    """List access requests, pending ones by default (oldest first)."""
    condition = AccessRequest.status == status
    rows = await session.execute(
        select(AccessRequest, User.email, Cohort.name)
        .join(User, User.id == AccessRequest.user_id)
        .outerjoin(Cohort, Cohort.id == AccessRequest.cohort_id)
        .where(condition)
        .order_by(AccessRequest.created_at)
        .limit(page.limit)
        .offset(page.offset)
    )
    total = await session.scalar(select(func.count(AccessRequest.id)).where(condition)) or 0
    items = [
        AccessRequestOut(
            id=request.id,
            user_email=email,
            message=request.message,
            status=request.status,
            created_at=request.created_at,
            reviewed_at=request.reviewed_at,
            cohort_name=cohort_name,
        )
        for request, email, cohort_name in rows
    ]
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


@router.post("/{request_id}/review")
async def review_request(
    request_id: uuid.UUID,
    data: ReviewIn,
    background: BackgroundTasks,
    actor: ActorDep,
    session: SessionDep,
    state: StateDep,
) -> MessageOut:
    """Approve a request into a cohort the actor manages, or reject it."""
    message = await staff.review_access_request(
        session,
        state.store,
        state.settings,
        actor,
        request_id,
        approve=data.approve,
        cohort_id=data.cohort_id,
    )
    if message:
        background.add_task(deliver, state.email, message)
    return MessageOut(message="Request approved." if data.approve else "Request rejected.")
