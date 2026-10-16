"""Gemini text generation with streaming, built on the google-genai SDK."""

import logging
import time
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass

from google import genai
from google.genai import errors, types

from app.core.exceptions import ServiceUnavailableError
from app.core.settings import Settings

logger = logging.getLogger(__name__)

_FINISH_REASON_MESSAGES = {
    "SAFETY": "[Response blocked by safety filters. Try rephrasing your prompt.]",
    "RECITATION": "[Response blocked due to potential recitation of training data.]",
    "MAX_TOKENS": "[Response was truncated due to the token limit.]",
}
_NO_TEXT_MESSAGE = "[No text was returned. The model may have declined to respond.]"


class LLMError(ServiceUnavailableError):
    """The model call failed; the message is safe to show to users."""

    code = "llm_error"


@dataclass(frozen=True, slots=True)
class PromptRequest:
    """A single-turn prompt."""

    user_prompt: str
    system_prompt: str = ""
    temperature: float = 1.0


@dataclass(frozen=True, slots=True)
class GenerationResult:
    """The complete answer, yielded last by `LLMService.stream`."""

    text: str
    tokens_used: int | None
    latency_seconds: float


class LLMService(ABC):
    """Contract every text-generation backend must satisfy."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Human-friendly model name."""

    @abstractmethod
    def stream(self, prompt: PromptRequest) -> AsyncIterator[str | GenerationResult]:
        """Yield text chunks, then one GenerationResult."""


def _finish_reason_message(candidate: types.Candidate | None) -> str:
    """Explain why a candidate produced no text."""
    reason = str(getattr(candidate, "finish_reason", "") or "").upper()
    for key, message in _FINISH_REASON_MESSAGES.items():
        if key in reason:
            return message
    return _NO_TEXT_MESSAGE


class GeminiService(LLMService):
    """Google Gemini implementation."""

    def __init__(self, settings: Settings) -> None:
        if settings.gemini_api_key is None:
            raise ValueError("GEMINI_API_KEY is not set")
        self._client = genai.Client(api_key=settings.gemini_api_key.get_secret_value())
        self._model_id = settings.gemini_model_id
        self._model_name = settings.gemini_model_name
        self._max_output_tokens = settings.max_output_tokens

    @property
    def model_name(self) -> str:
        return self._model_name

    async def stream(self, prompt: PromptRequest) -> AsyncIterator[str | GenerationResult]:
        config = types.GenerateContentConfig(
            system_instruction=prompt.system_prompt.strip() or None,
            temperature=prompt.temperature,
            max_output_tokens=self._max_output_tokens,
        )
        started = time.perf_counter()
        parts: list[str] = []
        last: types.GenerateContentResponse | None = None
        try:
            async for last in await self._client.aio.models.generate_content_stream(
                model=self._model_id, contents=prompt.user_prompt, config=config
            ):
                if last.text:
                    parts.append(last.text)
                    yield last.text
        except errors.APIError as exc:
            logger.exception("Gemini API call failed")
            raise LLMError(f"The model is unavailable right now (error {exc.code}).") from exc

        text = "".join(parts)
        if not text:
            candidates = (last.candidates if last else None) or []
            text = _finish_reason_message(candidates[0] if candidates else None)
            yield text
        usage = last.usage_metadata if last else None
        yield GenerationResult(
            text=text,
            tokens_used=usage.total_token_count if usage else None,
            latency_seconds=time.perf_counter() - started,
        )


def create_llm_service(settings: Settings) -> LLMService | None:
    """Build the LLM service, or None when no API key is configured."""
    if settings.gemini_api_key is None:
        logger.warning("GEMINI_API_KEY is not set; LLM features are disabled")
        return None
    return GeminiService(settings)
