"""Password policy: length rules and a k-anonymity check against known breaches."""

import hashlib
import logging

import httpx

from app.core.exceptions import AppError

logger = logging.getLogger(__name__)

MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 128
_HIBP_URL = "https://api.pwnedpasswords.com/range/{prefix}"


class WeakPasswordError(AppError):
    """The password does not meet the policy."""

    code = "weak_password"


async def is_breached(password: str, http: httpx.AsyncClient) -> bool:
    """Return True if the password appears in Have I Been Pwned; fail open on errors.

    Only the first five hex characters of the SHA-1 hash leave the server.
    """
    digest = hashlib.sha1(password.encode(), usedforsecurity=False).hexdigest().upper()
    prefix, suffix = digest[:5], digest[5:]
    try:
        response = await http.get(
            _HIBP_URL.format(prefix=prefix), headers={"Add-Padding": "true"}, timeout=3.0
        )
        response.raise_for_status()
    except httpx.HTTPError:
        logger.warning("Breached-password check unavailable")
        return False
    return any(
        line.split(":", 1)[0] == suffix and not line.endswith(":0")
        for line in response.text.splitlines()
    )


async def check_password(password: str, email: str, http: httpx.AsyncClient) -> None:
    """Raise WeakPasswordError if the password is unsuitable."""
    local_part = email.split("@", 1)[0].lower()
    if len(local_part) >= 4 and local_part in password.lower():
        raise WeakPasswordError("The password must not contain your e-mail address.")
    if len(set(password)) < 5:
        raise WeakPasswordError("The password is too repetitive.")
    if await is_breached(password, http):
        raise WeakPasswordError(
            "This password appeared in a known data breach. Please choose another one."
        )
