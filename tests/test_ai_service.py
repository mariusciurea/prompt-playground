from types import SimpleNamespace

import pytest
from google.genai import errors

from src.config import Settings
from src.models import PromptData
from src.services.ai_service import AIServiceError, GeminiService


def _chunk(text=None, tokens=None, finish_reason=None):
    return SimpleNamespace(
        text=text,
        usage_metadata=SimpleNamespace(total_token_count=tokens) if tokens else None,
        candidates=[SimpleNamespace(finish_reason=finish_reason)] if finish_reason else [],
    )


class FakeModels:
    def __init__(self, chunks=None, error=None):
        self._chunks, self._error, self.calls = chunks or [], error, []

    def generate_content_stream(self, **kwargs):
        self.calls.append(kwargs)
        if self._error:
            raise self._error
        yield from self._chunks


@pytest.fixture
def make_service(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    def _make(models: FakeModels) -> GeminiService:
        service = GeminiService(Settings())
        service._client = SimpleNamespace(models=models)
        return service

    return _make


def test_streams_chunks_and_collects_metadata(make_service):
    models = FakeModels([_chunk("Hello "), _chunk("world", tokens=42)])
    received = []

    response = make_service(models).generate_response(
        PromptData(system_prompt="Be brief", user_prompt="Hi", temperature=0.3),
        on_chunk=received.append,
    )

    assert received == ["Hello ", "world"]
    assert response.response_text == "Hello world"
    assert response.tokens_used == 42
    assert response.temperature == 0.3
    assert response.latency_seconds is not None
    config = models.calls[0]["config"]
    assert config.system_instruction == "Be brief"
    assert config.temperature == 0.3


def test_blank_system_prompt_is_not_sent(make_service):
    models = FakeModels([_chunk("ok")])
    make_service(models).generate_response(PromptData(system_prompt="  ", user_prompt="Hi"))
    assert models.calls[0]["config"].system_instruction is None


def test_explains_blocked_responses(make_service):
    models = FakeModels([_chunk(None, finish_reason="FinishReason.SAFETY")])
    response = make_service(models).generate_response(PromptData(user_prompt="Hi"))
    assert "safety" in response.response_text.lower()


def test_api_errors_become_service_errors(make_service):
    error = errors.APIError(429, {"error": {"message": "quota exceeded"}})
    with pytest.raises(AIServiceError, match="quota exceeded"):
        make_service(FakeModels(error=error)).generate_response(PromptData(user_prompt="Hi"))


def test_service_requires_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        GeminiService(Settings())
