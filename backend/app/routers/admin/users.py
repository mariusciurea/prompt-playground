"""User management endpoints."""

import uuid

from fastapi import APIRouter, status

from app.core.state import StateDep
from app.crud import stats
from app.crud.cohorts import owned_member_emails
from app.data_models.admin import AdminUserOut, UserUpdateIn
from app.data_models.common import Page
from app.database.session import SessionDep
from app.db_models import Role, User
from app.domain import staff
from app.domain.quota import quota_day
from app.routers.admin.deps import ActorDep
from app.routers.helpers import PaginationDep

router = APIRouter(prefix="/users")


def _user_out(user: User, prompts_today: int) -> AdminUserOut:
    return AdminUserOut(
        id=user.id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        email_verified=user.email_verified_at is not None,
        totp_enabled=user.totp_enabled_at is not None,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
        prompts_today=prompts_today,
    )


@router.get("")
async def list_users(
    actor: ActorDep,
    session: SessionDep,
    state: StateDep,
    page: PaginationDep,
    search: str | None = None,
    role: Role | None = None,
) -> Page[AdminUserOut]:
    """List users; instructors only see members of their cohorts."""
    rows, total = await stats.list_users(
        session,
        emails=None if actor.is_admin else owned_member_emails(actor.user.id),
        search=search,
        role=role,
        today=quota_day(state.settings),
        limit=page.limit,
        offset=page.offset,
    )
    return Page(
        items=[_user_out(*row) for row in rows],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.patch("/{user_id}")
async def update_user(
    user_id: uuid.UUID, data: UserUpdateIn, actor: ActorDep, session: SessionDep, state: StateDep
) -> AdminUserOut:
    """Change a user's role or status (admins only)."""
    user = await staff.update_user(
        session, state.store, actor, user_id, role=data.role, is_active=data.is_active
    )
    return _user_out(user, 0)


@router.post("/{user_id}/reset-2fa", status_code=status.HTTP_204_NO_CONTENT)
async def reset_two_factor(user_id: uuid.UUID, actor: ActorDep, session: SessionDep) -> None:
    """Clear a user's two-factor setup (admins only)."""
    await staff.reset_two_factor(session, actor, user_id)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: uuid.UUID, actor: ActorDep, session: SessionDep) -> None:
    """Delete a user and their data (admins only)."""
    await staff.delete_user(session, actor, user_id)
