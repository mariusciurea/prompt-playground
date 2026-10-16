"""Create and validate JSON Web Tokens used for API authentication."""

import uuid
from datetime import timedelta

import jwt

from app.core.exceptions import AuthenticationError
from app.core.settings import Settings
from app.database.base import utcnow

_ISSUER = "ai-playground"
_AUDIENCE = "ai-playground-web"


def create_access_token(user_id: uuid.UUID, settings: Settings) -> str:
    """Issue a short-lived access token for a user."""
    now = utcnow()
    claims = {
        "sub": str(user_id),
        "iss": _ISSUER,
        "aud": _AUDIENCE,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
        "jti": uuid.uuid4().hex,
        "typ": "access",
    }
    return jwt.encode(
        claims, settings.jwt_secret_key.get_secret_value(), algorithm=settings.jwt_algorithm
    )


def decode_access_token(token: str, settings: Settings) -> uuid.UUID:
    """Validate an access token and return the user ID it was issued for."""
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            audience=_AUDIENCE,
            issuer=_ISSUER,
            options={"require": ["exp", "iat", "sub", "typ"]},
        )
        if claims["typ"] != "access":
            raise AuthenticationError("Invalid token.")
        return uuid.UUID(claims["sub"])
    except (jwt.PyJWTError, ValueError) as exc:
        raise AuthenticationError("Session expired. Please sign in again.") from exc
