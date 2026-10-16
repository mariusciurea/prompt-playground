"""FastAPI dependencies that resolve the authenticated user and enforce access rules."""

from typing import Annotated

from fastapi import Depends, Request

from app.auth.cookies import ACCESS_COOKIE
from app.auth.jwt import decode_access_token
from app.core.exceptions import AuthenticationError, NoAccessError, PermissionDeniedError
from app.core.rate_limit import API_PER_USER
from app.core.state import SettingsDep, StateDep
from app.database.session import SessionDep
from app.db_models import Role, User
from app.domain.access import get_access


class TwoFactorSetupRequiredError(PermissionDeniedError):
    """Staff must enable two-factor authentication before using staff features."""

    code = "totp_setup_required"


async def get_current_user(request: Request, session: SessionDep, settings: SettingsDep) -> User:
    """Return the signed-in user from the access-token cookie."""
    token = request.cookies.get(ACCESS_COOKIE)
    if not token:
        raise AuthenticationError("Please sign in.")
    user = await session.get(User, decode_access_token(token, settings))
    if user is None or not user.is_active or user.email_verified_at is None:
        raise AuthenticationError("Please sign in.")
    return user


async def get_rate_limited_user(
    user: Annotated[User, Depends(get_current_user)], state: StateDep
) -> User:
    """Apply the per-user API rate limit (admins are exempt)."""
    if user.role is not Role.ADMIN:
        await state.rate_limiter.hit(API_PER_USER, str(user.id))
    return user


CurrentUser = Annotated[User, Depends(get_rate_limited_user)]


async def require_access(user: CurrentUser, session: SessionDep, state: StateDep) -> User:
    """Allow only users with active course access."""
    status = await get_access(session, state.store, user)
    if not status.has_access:
        raise NoAccessError("You don't have course access yet. Request it from your dashboard.")
    return user


async def require_staff(user: CurrentUser) -> User:
    """Allow admins and instructors who have two-factor authentication enabled."""
    if not user.is_staff:
        raise PermissionDeniedError("Staff only.")
    if user.totp_enabled_at is None:
        raise TwoFactorSetupRequiredError("Enable two-factor authentication to use staff tools.")
    return user


async def require_admin(user: Annotated[User, Depends(require_staff)]) -> User:
    """Allow admins only."""
    if user.role is not Role.ADMIN:
        raise PermissionDeniedError("Admins only.")
    return user


AccessUser = Annotated[User, Depends(require_access)]
StaffUser = Annotated[User, Depends(require_staff)]
AdminUser = Annotated[User, Depends(require_admin)]
