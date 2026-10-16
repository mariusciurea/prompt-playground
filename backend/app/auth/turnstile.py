"""Server-side verification of Cloudflare Turnstile challenges."""

import logging

import httpx

from app.core.exceptions import PermissionDeniedError
from app.core.settings import Settings

logger = logging.getLogger(__name__)

_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


class BotCheckFailedError(PermissionDeniedError):
    """The Turnstile challenge was missing or invalid."""

    code = "bot_check_failed"


async def verify_turnstile(
    token: str | None, ip: str | None, *, settings: Settings, http: httpx.AsyncClient
) -> None:
    """Raise unless the Turnstile token is valid; no-op when Turnstile is not configured."""
    if settings.turnstile_secret_key is None:
        return
    if not token:
        raise BotCheckFailedError("Please complete the bot check.")
    data = {"secret": settings.turnstile_secret_key.get_secret_value(), "response": token}
    if ip:
        data["remoteip"] = ip
    try:
        response = await http.post(_VERIFY_URL, data=data, timeout=5.0)
        success = bool(response.json().get("success"))
    except (httpx.HTTPError, ValueError):
        logger.warning("Turnstile verification request failed")
        success = False
    if not success:
        raise BotCheckFailedError("Bot check failed. Please try again.")
