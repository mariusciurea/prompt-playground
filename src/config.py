"""
Application settings.

All configuration comes from environment variables (or the project's ``.env``
file) and is validated by pydantic-settings. Use :func:`get_settings` to obtain
the shared instance instead of instantiating :class:`Settings` directly.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Typed, validated application settings."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Gemini API
    gemini_api_key: SecretStr | None = Field(default=None, description="Google AI Studio API key.")
    gemini_model_id: str = Field(
        default="gemini-3-flash-preview",
        description="Model used by the Playground and Engage views.",
    )
    gemini_model_name: str = Field(
        default="Gemini 3", description="Human-friendly model name shown in the UI."
    )
    agent_model_id: str = Field(
        default="gemini-3.5-flash",
        description="Model used by the Reservation agent.",
    )

    # Prompt limits and generation defaults
    max_prompt_length: int = Field(default=10_000, gt=0)
    default_temperature: float = Field(default=1.0, ge=0.0, le=2.0)

    # App
    app_title: str = "AI Playground"
    app_icon: str = "🎮"
    documentation_url: str = "https://www.promptingguide.ai/techniques"
    log_level: str = "INFO"

    @property
    def has_api_key(self) -> bool:
        """Whether a non-empty API key is configured."""
        return bool(self.gemini_api_key and self.gemini_api_key.get_secret_value())

    def require_api_key(self) -> str:
        """Return the API key or raise a ``ValueError`` explaining how to set it."""
        if not self.has_api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set. Add it to the .env file or export it "
                "as an environment variable."
            )
        return self.gemini_api_key.get_secret_value()  # type: ignore[union-attr]


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings instance."""
    return Settings()
