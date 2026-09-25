import pytest
from pydantic import ValidationError

from src.config import Settings


def test_defaults_without_environment():
    settings = Settings()
    assert not settings.has_api_key
    assert settings.gemini_model_id == "gemini-3-flash-preview"
    assert settings.max_prompt_length == 10_000


def test_reads_environment(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "secret")
    monkeypatch.setenv("GEMINI_MODEL_ID", "custom-model")
    settings = Settings()
    assert settings.require_api_key() == "secret"
    assert settings.gemini_model_id == "custom-model"
    assert "secret" not in repr(settings)


def test_missing_key_raises_helpful_error():
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        Settings().require_api_key()


def test_validates_values(monkeypatch):
    monkeypatch.setenv("DEFAULT_TEMPERATURE", "5")
    with pytest.raises(ValidationError):
        Settings()
