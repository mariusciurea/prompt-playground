"""The e-mail backend resolves correctly and production rejects a console-only setup."""

import httpx
import pytest
from pydantic import ValidationError

from app.core.settings import EmailBackend, Environment, Settings
from app.domain.email import (
    ConsoleEmailSender,
    ResendEmailSender,
    SmtpEmailSender,
    create_email_sender,
)


def _settings(database_url: str, **overrides: object) -> Settings:
    base = dict(
        _env_file=None,
        environment=Environment.TEST,
        database_url=database_url,
        jwt_secret_key="x" * 40,
        totp_encryption_key="k" * 44,
        cookie_secure=False,
    )
    return Settings(**{**base, **overrides})  # type: ignore[arg-type]


def test_auto_prefers_resend_then_smtp_then_console(database_url):
    http = httpx.AsyncClient()
    assert isinstance(create_email_sender(_settings(database_url), http), ConsoleEmailSender)
    assert isinstance(
        create_email_sender(_settings(database_url, resend_api_key="re_x"), http),
        ResendEmailSender,
    )
    smtp = _settings(
        database_url, smtp_host="smtp.gmail.com", smtp_username="me@gmail.com", smtp_password="app"
    )
    assert isinstance(create_email_sender(smtp, http), SmtpEmailSender)


def test_explicit_backend_is_honored(database_url):
    http = httpx.AsyncClient()
    forced = _settings(database_url, email_backend=EmailBackend.CONSOLE, resend_api_key="re_x")
    assert isinstance(create_email_sender(forced, http), ConsoleEmailSender)


def test_production_requires_a_real_email_transport(database_url):
    common = dict(
        environment="production",
        redis_url="redis://localhost:6379/0",
        turnstile_secret_key="secret",
    )
    with pytest.raises(ValidationError, match="e-mail transport"):
        _settings(database_url, cookie_secure=True, **common)

    # SMTP started but incomplete is rejected too.
    with pytest.raises(ValidationError, match="SMTP requires"):
        _settings(
            database_url,
            cookie_secure=True,
            email_backend="smtp",
            smtp_host="smtp.gmail.com",
            **common,
        )

    # A complete SMTP setup is accepted.
    ok = _settings(
        database_url,
        cookie_secure=True,
        smtp_host="smtp.gmail.com",
        smtp_username="me@gmail.com",
        smtp_password="app-password",
        **common,
    )
    assert ok.resolved_email_backend is EmailBackend.SMTP
