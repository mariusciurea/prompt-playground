"""Endpoints for the signed-in user's own account."""

from fastapi import APIRouter, Response, status

from app.auth.cookies import clear_auth_cookies
from app.auth.dependencies import CurrentUser
from app.core.state import StateDep
from app.crud import access_requests
from app.data_models.auth import DeleteAccountIn, TotpCodeIn, TotpSetupOut, UserOut
from app.data_models.common import MessageOut
from app.data_models.me import AccessOut, ChangePasswordIn, MeOut, QuotaOut
from app.database.session import SessionDep
from app.domain import auth, quota
from app.domain.access import get_access

router = APIRouter(prefix="/me", tags=["me"])


@router.get("")
async def me(user: CurrentUser, session: SessionDep, state: StateDep) -> MeOut:
    """Return the account, its course access, and today's quota."""
    access = await get_access(session, state.store, user)
    pending = False if access.has_access else await access_requests.has_pending(session, user.id)
    return MeOut(
        user=UserOut.from_user(user),
        access=AccessOut.build(access, pending_request=pending),
        quota=QuotaOut.build(await quota.get_status(session, user, state.settings)),
    )


@router.post("/password")
async def change_password(
    data: ChangePasswordIn,
    response: Response,
    user: CurrentUser,
    session: SessionDep,
    state: StateDep,
) -> MessageOut:
    """Change the password; all sessions, including this one, are signed out."""
    await auth.change_password(session, user, data.current_password, data.new_password, state.http)
    clear_auth_cookies(response, state.settings)
    return MessageOut(message="Password changed. Please sign in again.")


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    data: DeleteAccountIn,
    response: Response,
    user: CurrentUser,
    session: SessionDep,
    state: StateDep,
) -> None:
    """Delete the account and all its data."""
    await auth.delete_account(session, user, data.password)
    clear_auth_cookies(response, state.settings)


@router.post("/totp/setup")
async def totp_setup(user: CurrentUser, session: SessionDep, state: StateDep) -> TotpSetupOut:
    """Start two-factor setup and return the secret for an authenticator app."""
    secret, uri = await auth.start_totp_setup(session, user, state.settings)
    return TotpSetupOut(secret=secret, otpauth_uri=uri)


@router.post("/totp/enable")
async def totp_enable(
    data: TotpCodeIn, user: CurrentUser, session: SessionDep, state: StateDep
) -> MessageOut:
    """Confirm the first code and turn on two-factor authentication."""
    await auth.enable_totp(session, user, data.code, state.settings, state.store)
    return MessageOut(message="Two-factor authentication is on.")
