"""TOTP two-factor authentication: secret generation, encryption at rest, and code checks."""

import pyotp
from cryptography.fernet import Fernet

from app.core.settings import Settings
from app.core.store import Store

_CODE_REUSE_TTL = 90  # covers the ±1 step validity window


def generate_secret() -> str:
    """Return a new base32 TOTP secret."""
    return pyotp.random_base32()


def encrypt_secret(secret: str, settings: Settings) -> str:
    """Encrypt a TOTP secret for storage."""
    return Fernet(settings.totp_encryption_key.get_secret_value()).encrypt(secret.encode()).decode()


def decrypt_secret(token: str, settings: Settings) -> str:
    """Decrypt a stored TOTP secret."""
    return Fernet(settings.totp_encryption_key.get_secret_value()).decrypt(token.encode()).decode()


def provisioning_uri(secret: str, email: str, issuer: str) -> str:
    """Return the otpauth:// URI an authenticator app scans."""
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name=issuer)


async def verify_code(secret: str, code: str, *, replay_key: str, store: Store) -> bool:
    """Check a 6-digit code, rejecting a code that was already used."""
    if not pyotp.TOTP(secret).verify(code, valid_window=1):
        return False
    return await store.set_if_absent(f"totp_used:{replay_key}:{code}", "1", _CODE_REUSE_TTL)
