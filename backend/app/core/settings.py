"""Application settings loaded from environment variables and an optional .env file."""

from enum import StrEnum
from functools import lru_cache
from typing import Self
from zoneinfo import ZoneInfo

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    """Deployment environment."""

    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class EmailBackend(StrEnum):
    """How outgoing e-mail is delivered."""

    AUTO = "auto"  # pick based on what is configured (resend → smtp → console)
    CONSOLE = "console"  # log messages instead of sending (development)
    RESEND = "resend"  # Resend HTTP API (needs a verified domain)
    SMTP = "smtp"  # any SMTP server, e.g. Gmail with an app password (no domain needed)


class Settings(BaseSettings):
    """Typed application configuration.

    Values come from environment variables, then from a `.env` file in the
    working directory, then from the defaults below. Names are case-insensitive.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
    )

    app_name: str = Field(default="AI Playground", description="Human-readable application name.")
    environment: Environment = Field(default=Environment.DEVELOPMENT)
    log_level: str = Field(default="INFO", description="Root log level, e.g. DEBUG, INFO.")
    log_json: bool = Field(default=False, description="Emit logs as JSON lines.")

    database_url: str = Field(description="SQLAlchemy async URL (postgresql+asyncpg://...).")
    redis_url: str | None = Field(
        default=None, description="Redis URL. Required in production; in-memory store otherwise."
    )

    public_base_url: str = Field(
        default="http://localhost:5173", description="Origin of the web app, used in e-mail links."
    )
    client_ip_header: str | None = Field(
        default=None,
        description="Trusted header carrying the client IP, set by the reverse proxy.",
    )

    jwt_secret_key: SecretStr = Field(min_length=32, description="Secret used to sign JWTs.")
    jwt_algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=15, gt=0)
    refresh_token_expire_days: int = Field(default=14, gt=0)
    cookie_secure: bool = Field(default=True, description="Mark auth cookies Secure (HTTPS only).")
    totp_encryption_key: SecretStr = Field(
        description="Fernet key that encrypts TOTP secrets at rest."
    )

    turnstile_secret_key: SecretStr | None = Field(
        default=None, description="Cloudflare Turnstile secret. Verification is skipped if unset."
    )
    email_backend: EmailBackend = Field(
        default=EmailBackend.AUTO, description="Which e-mail transport to use."
    )
    resend_api_key: SecretStr | None = Field(default=None, description="Resend API key.")
    smtp_host: str | None = Field(default=None, description="SMTP host, e.g. smtp.gmail.com.")
    smtp_port: int = Field(default=587, gt=0, le=65535, description="SMTP port (587 = STARTTLS).")
    smtp_username: str | None = Field(default=None, description="SMTP login (e.g. your Gmail).")
    smtp_password: SecretStr | None = Field(
        default=None, description="SMTP password (a Gmail app password, not the account password)."
    )
    email_from: str = Field(default="AI Playground <noreply@example.com>")

    gemini_api_key: SecretStr | None = Field(default=None, description="Google AI Studio key.")
    gemini_model_id: str = Field(default="gemini-3-flash-preview")
    gemini_model_name: str = Field(default="Gemini 3")
    agent_model_id: str = Field(default="gemini-3.5-flash")
    max_prompt_length: int = Field(default=10_000, gt=0, le=100_000)
    max_output_tokens: int = Field(default=4096, gt=0)
    default_temperature: float = Field(default=1.0, ge=0.0, le=2.0)

    daily_prompt_limit: int = Field(default=70, gt=0)
    quota_timezone: str = Field(default="Europe/Bucharest")
    instructors_exempt_from_quota: bool = Field(default=True)

    history_retention_days: int = Field(
        default=30, gt=0, description="Days to keep history after a user's last cohort ends."
    )
    unverified_account_ttl_hours: int = Field(default=48, gt=0)

    @property
    def is_production(self) -> bool:
        """Whether the app runs in production."""
        return self.environment is Environment.PRODUCTION

    @property
    def quota_zone(self) -> ZoneInfo:
        """Time zone in which the daily quota resets."""
        return ZoneInfo(self.quota_timezone)

    @property
    def resolved_email_backend(self) -> EmailBackend:
        """The transport AUTO resolves to, given what is configured."""
        if self.email_backend is not EmailBackend.AUTO:
            return self.email_backend
        if self.resend_api_key is not None:
            return EmailBackend.RESEND
        if self.smtp_host is not None:
            return EmailBackend.SMTP
        return EmailBackend.CONSOLE

    @field_validator("quota_timezone")
    @classmethod
    def _check_timezone(cls, value: str) -> str:
        ZoneInfo(value)  # raises for unknown zones
        return value

    @model_validator(mode="after")
    def _check_production_requirements(self) -> Self:
        if not self.is_production:
            return self
        missing = [
            name
            for name, value in (
                ("REDIS_URL", self.redis_url),
                ("TURNSTILE_SECRET_KEY", self.turnstile_secret_key),
            )
            if value is None
        ]
        if missing:
            raise ValueError(f"Missing required production settings: {', '.join(missing)}")
        if self.resolved_email_backend is EmailBackend.CONSOLE:
            raise ValueError(
                "No e-mail transport configured for production: set RESEND_API_KEY, or "
                "SMTP_HOST/SMTP_USERNAME/SMTP_PASSWORD."
            )
        if self.resolved_email_backend is EmailBackend.SMTP and (
            self.smtp_host is None or self.smtp_username is None or self.smtp_password is None
        ):
            raise ValueError("SMTP requires SMTP_HOST, SMTP_USERNAME and SMTP_PASSWORD.")
        if not self.cookie_secure:
            raise ValueError("COOKIE_SECURE must be true in production")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings, loaded once."""
    return Settings()  # required values come from the environment
