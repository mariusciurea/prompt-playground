"""Hash and verify user passwords and opaque tokens."""

import hashlib
import secrets

from anyio import to_thread
from pwdlib import PasswordHash

_hasher = PasswordHash.recommended()  # Argon2id
_DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(16))


async def hash_password(password: str) -> str:
    """Hash a password off the event loop."""
    return await to_thread.run_sync(_hasher.hash, password)


async def verify_password(password: str, password_hash: str | None) -> tuple[bool, str | None]:
    """Check a password; return (valid, new hash if parameters were upgraded).

    A missing hash is checked against a dummy hash so that unknown accounts
    take as long as known ones.
    """
    valid, updated = await to_thread.run_sync(
        _hasher.verify_and_update, password, password_hash or _DUMMY_HASH
    )
    return (valid and password_hash is not None), updated


def generate_token() -> str:
    """Return a URL-safe random token with 256 bits of entropy."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Hash an opaque token for storage; tokens are random, so SHA-256 suffices."""
    return hashlib.sha256(token.encode()).hexdigest()
