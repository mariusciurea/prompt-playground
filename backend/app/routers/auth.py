"""Authentication endpoints: registration, verification, sign-in, sessions, password reset."""

import secrets

from fastapi import APIRouter, BackgroundTasks, Request, Response, status

from app.auth.cookies import REFRESH_COOKIE, clear_auth_cookies, set_auth_cookies, set_csrf_cookie
from app.auth.turnstile import verify_turnstile
from app.core.exceptions import AuthenticationError
from app.core.middleware import CSRF_COOKIE
from app.core.rate_limit import (
    EMAIL_ACTION_PER_EMAIL,
    EMAIL_ACTION_PER_IP,
    LOGIN_PER_EMAIL,
    LOGIN_PER_IP,
    REFRESH_PER_IP,
    REGISTER_PER_IP,
)
from app.core.state import ClientIpDep, StateDep
from app.data_models.auth import (
    CsrfOut,
    EmailIn,
    LoginIn,
    RegisterIn,
    ResetPasswordIn,
    TokenIn,
    UserOut,
)
from app.data_models.common import MessageOut
from app.database.session import SessionDep
from app.domain import auth
from app.domain.email import deliver

router = APIRouter(prefix="/auth", tags=["auth"])

_CHECK_INBOX = "If the address can be used, we've sent you an e-mail. Check your inbox."


@router.get("/csrf")
async def csrf(request: Request, response: Response, state: StateDep) -> CsrfOut:
    """Issue (or repeat) the CSRF token the client must echo on unsafe requests."""
    token = request.cookies.get(CSRF_COOKIE) or secrets.token_urlsafe(32)
    set_csrf_cookie(response, token, state.settings)
    return CsrfOut(csrf_token=token)


@router.post("/register", status_code=status.HTTP_202_ACCEPTED)
async def register(
    data: RegisterIn,
    background: BackgroundTasks,
    session: SessionDep,
    state: StateDep,
    ip: ClientIpDep,
) -> MessageOut:
    """Create an account; the reply is the same whether or not the address exists."""
    await state.rate_limiter.hit(REGISTER_PER_IP, ip)
    await verify_turnstile(data.turnstile_token, ip, settings=state.settings, http=state.http)
    message = await auth.register(
        session, email=data.email, password=data.password, settings=state.settings, http=state.http
    )
    if message:
        background.add_task(deliver, state.email, message)
    return MessageOut(message=_CHECK_INBOX)


@router.post("/verify-email")
async def verify_email(
    data: TokenIn, session: SessionDep, state: StateDep, ip: ClientIpDep
) -> MessageOut:
    """Confirm an e-mail address."""
    await state.rate_limiter.hit(LOGIN_PER_IP, ip)
    await auth.verify_email(session, data.token)
    return MessageOut(message="Your e-mail is confirmed. You can sign in now.")


@router.post("/login")
async def login(
    data: LoginIn, response: Response, session: SessionDep, state: StateDep, ip: ClientIpDep
) -> UserOut:
    """Sign in and receive session cookies."""
    await state.rate_limiter.hit(LOGIN_PER_IP, ip)
    await state.rate_limiter.hit(LOGIN_PER_EMAIL, data.email)
    await verify_turnstile(data.turnstile_token, ip, settings=state.settings, http=state.http)
    user, issued = await auth.login(
        session,
        email=data.email,
        password=data.password,
        totp_code=data.totp_code,
        settings=state.settings,
        store=state.store,
    )
    set_auth_cookies(response, issued.access, issued.refresh, state.settings)
    return UserOut.from_user(user)


@router.post("/refresh")
async def refresh(
    request: Request, response: Response, session: SessionDep, state: StateDep, ip: ClientIpDep
) -> UserOut:
    """Rotate the refresh token and issue a new access token."""
    await state.rate_limiter.hit(REFRESH_PER_IP, ip)
    raw = request.cookies.get(REFRESH_COOKIE)
    if not raw:
        raise AuthenticationError("Please sign in.")
    user, issued = await auth.refresh(session, raw, state.settings)
    set_auth_cookies(response, issued.access, issued.refresh, state.settings)
    return UserOut.from_user(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request, response: Response, session: SessionDep, state: StateDep
) -> None:
    """End the current session."""
    await auth.logout(session, request.cookies.get(REFRESH_COOKIE))
    clear_auth_cookies(response, state.settings)


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(
    data: EmailIn,
    background: BackgroundTasks,
    session: SessionDep,
    state: StateDep,
    ip: ClientIpDep,
) -> MessageOut:
    """Send a password reset link if the account exists."""
    await state.rate_limiter.hit(EMAIL_ACTION_PER_IP, ip)
    await state.rate_limiter.hit(EMAIL_ACTION_PER_EMAIL, data.email)
    await verify_turnstile(data.turnstile_token, ip, settings=state.settings, http=state.http)
    message = await auth.forgot_password(session, data.email, state.settings)
    if message:
        background.add_task(deliver, state.email, message)
    return MessageOut(message=_CHECK_INBOX)


@router.post("/reset-password")
async def reset_password(
    data: ResetPasswordIn, response: Response, session: SessionDep, state: StateDep, ip: ClientIpDep
) -> MessageOut:
    """Choose a new password; every existing session is signed out."""
    await state.rate_limiter.hit(LOGIN_PER_IP, ip)
    await auth.reset_password(session, data.token, data.new_password, state.http)
    clear_auth_cookies(response, state.settings)
    return MessageOut(message="Your password was changed. Sign in with the new one.")
