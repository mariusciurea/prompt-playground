"""AI service abstraction and its Gemini implementation."""

import logging
import time
from abc import ABC, abstractmethod
from collections.abc import Callable

from google import genai
from google.genai import errors, types

from src.config import Settings
from src.models import ModelResponse, PromptData

logger = logging.getLogger(__name__)

ChunkCallback = Callable[[str], None]

_FINISH_REASON_MESSAGES = {
    "SAFETY": "[Response blocked by safety filters. Try rephrasing your prompt.]",
    "RECITATION": "[Response blocked due to potential recitation of training data.]",
    "MAX_TOKENS": "[Response was truncated due to the token limit.]",
}
_NO_TEXT_MESSAGE = "[No text was returned. The model may have declined to respond.]"


class AIServiceError(RuntimeError):
    """Raised when the AI backend fails; the message is safe to show to users."""


class AIService(ABC):
    """Contract every AI backend must satisfy."""

    @abstractmethod
    def generate_response(
        self, prompt_data: PromptData, on_chunk: ChunkCallback | None = None
    ) -> ModelResponse:
        """Generate a response, calling ``on_chunk`` with each streamed text piece."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Human-friendly model name."""


def _finish_reason_message(candidate: types.Candidate | None) -> str:
    """Explain why a candidate produced no text."""
    reason = str(getattr(candidate, "finish_reason", "") or "").upper()
    for key, message in _FINISH_REASON_MESSAGES.items():
        if key in reason:
            return message
    return _NO_TEXT_MESSAGE


class GeminiService(AIService):
    """Google Gemini implementation built on the ``google-genai`` SDK."""

    def __init__(self, settings: Settings) -> None:
        self._client = genai.Client(api_key=settings.require_api_key())
        self._model_id = settings.gemini_model_id
        self._model_name = settings.gemini_model_name

    @property
    def model_name(self) -> str:
        return self._model_name

    def generate_response(
        self, prompt_data: PromptData, on_chunk: ChunkCallback | None = None
    ) -> ModelResponse:
        config = types.GenerateContentConfig(
            system_instruction=prompt_data.system_prompt.strip() or None,
            temperature=prompt_data.temperature,
        )

        logger.info("Generating response with %s", self._model_id)
        started = time.perf_counter()
        parts: list[str] = []
        last_chunk: types.GenerateContentResponse | None = None

        try:
            for last_chunk in self._client.models.generate_content_stream(
                model=self._model_id,
                contents=prompt_data.user_prompt,
                config=config,
            ):
                if last_chunk.text:
                    parts.append(last_chunk.text)
                    if on_chunk:
                        on_chunk(last_chunk.text)
        except errors.APIError as exc:
            logger.exception("Gemini API call failed")
            raise AIServiceError(f"Gemini API error ({exc.code}): {exc.message}") from exc

        latency = time.perf_counter() - started
        text = "".join(parts)
        if not text:
            candidates = (last_chunk.candidates if last_chunk else None) or []
            text = _finish_reason_message(candidates[0] if candidates else None)

        usage = last_chunk.usage_metadata if last_chunk else None
        tokens = usage.total_token_count if usage else None
        logger.info("Response generated in %.2fs (%s tokens)", latency, tokens)

        return ModelResponse(
            model_name=self._model_name,
            response_text=text,
            user_prompt=prompt_data.user_prompt,
            system_prompt=prompt_data.system_prompt,
            tokens_used=tokens,
            latency_seconds=latency,
            temperature=prompt_data.temperature,
        )


def create_ai_service(settings: Settings) -> AIService:
    """Build the configured AI service (raises ``ValueError`` if misconfigured)."""
    return GeminiService(settings)
