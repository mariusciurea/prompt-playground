"""Auth and CSRF cookie names, scopes, and helpers."""

from fastapi import Response

from app.core.middleware import CSRF_COOKIE
from app.core.settings import Settings

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"
_ACCESS_PATH = "/api"
_REFRESH_PATH = "/api/auth"


def set_auth_cookies(response: Response, access: str, refresh: str, settings: Settings) -> None:
    """Attach httpOnly access and refresh cookies."""
    response.set_cookie(
        ACCESS_COOKIE,
        access,
        max_age=settings.access_token_expire_minutes * 60,
        path=_ACCESS_PATH,
        secure=settings.cookie_secure,
        httponly=True,
        samesite="strict",
    )
    response.set_cookie(
        REFRESH_COOKIE,
        refresh,
        max_age=settings.refresh_token_expire_days * 86400,
        path=_REFRESH_PATH,
        secure=settings.cookie_secure,
        httponly=True,
        samesite="strict",
    )


def clear_auth_cookies(response: Response, settings: Settings) -> None:
    """Remove the auth cookies."""
    for name, path in ((ACCESS_COOKIE, _ACCESS_PATH), (REFRESH_COOKIE, _REFRESH_PATH)):
        response.delete_cookie(
            name, path=path, secure=settings.cookie_secure, httponly=True, samesite="strict"
        )


def set_csrf_cookie(response: Response, token: str, settings: Settings) -> None:
    """Attach the CSRF cookie; it is readable by JS so it can be echoed in a header."""
    response.set_cookie(
        CSRF_COOKIE,
        token,
        path="/",
        secure=settings.cookie_secure,
        httponly=False,
        samesite="strict",
    )
