"""
AI service interfaces and implementations.

This module provides abstractions for AI model interactions
"""

import os
from abc import ABC, abstractmethod
from typing import Optional
from src.models.models import PromptData, ModelResponse
from src.config import GEMINI_MODEL_ID, GEMINI_MODEL_NAME
from datetime import datetime


def _extract_text_safely(response) -> str:
    """
    Safely extract text from a Gemini API response.

    response.text raises when the response has no valid parts (e.g. blocked by
    safety filters, finish_reason SAFETY/RECITATION/OTHER). This function
    handles those cases and returns a fallback message.
    """
    try:
        candidates = getattr(response, "candidates", None) or []
        if not candidates:
            return "[No response generated. The model may have blocked this request.]"

        candidate = candidates[0]
        content = getattr(candidate, "content", None)
        if not content:
            return _finish_reason_message(candidate)

        parts = getattr(content, "parts", None) or []
        if not parts:
            return _finish_reason_message(candidate)

        part = parts[0]
        text = getattr(part, "text", None)
        return text if text else ""

    except (AttributeError, IndexError, TypeError, ValueError):
        return "[Unable to parse the model response.]"


def _finish_reason_message(candidate) -> str:
    """Return a user-friendly message based on finish_reason."""
    reason = getattr(candidate, "finish_reason", None)
    reason_str = str(reason).upper() if reason is not None else ""
    if "SAFETY" in reason_str:
        return "[Response blocked by safety filters. Try rephrasing your prompt.]"
    if "RECITATION" in reason_str:
        return "[Response blocked due to potential recitation of training data.]"
    if "MAX_TOKENS" in reason_str:
        return "[Response was truncated due to token limit.]"
    return "[No text was returned. The model may have declined to respond.]"


class AIServiceInterface(ABC):
    """
    Abstract base class defining the interface for AI services
    """

    @abstractmethod
    def generate_response(self, prompt_data: PromptData) -> ModelResponse:
        """
        Generate a response from the AI model.

        Args:
            prompt_data: The prompt data containing system and user prompts

        Returns:
            ModelResponse: The generated response from the AI model
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """
        Get the name of the AI model.

        Returns:
            str: The model name
        """
        pass


class GeminiService(AIServiceInterface):
    """Google Gemini API implementation"""

    def __init__(self):
        """Initialize the Gemini service"""
        self._api_key = os.getenv("GEMINI_API_KEY")
        if not self._api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable is not set"
            )
        self._model_name = GEMINI_MODEL_NAME

    def generate_response(self, prompt_data: PromptData) -> ModelResponse:
        """
        Generate a response using the Gemini API.

        Args:
            prompt_data: The prompt data containing system and user prompts

        Returns:
            ModelResponse: The generated response from Gemini
        """
        import google.generativeai as genai

        genai.configure(api_key=self._api_key)

        model_kwargs = {}
        if prompt_data.system_prompt.strip():
            model_kwargs["system_instruction"] = prompt_data.system_prompt.strip()

        model = genai.GenerativeModel(GEMINI_MODEL_ID, **model_kwargs)
        response = model.generate_content(prompt_data.user_prompt)

        response_text = _extract_text_safely(response)
        tokens_used = None

        if hasattr(response, "usage_metadata") and response.usage_metadata:
            usage = response.usage_metadata
            total_tokens = getattr(usage, "total_token_count", None) or getattr(
                usage, "candidates_token_count", None
            )
            if total_tokens is not None:
                tokens_used = int(total_tokens)

        if tokens_used is None and response_text:
            tokens_used = len(response_text.split())

        return ModelResponse(
            model_name=self._model_name,
            response_text=response_text,
            user_prompt=prompt_data.user_prompt,
            system_prompt=prompt_data.system_prompt,
            timestamp=datetime.now(),
            tokens_used=tokens_used,
        )

    def get_model_name(self) -> str:
        """
        Get the model name

        Returns:
            str: The model name
        """
        return self._model_name


class AIServiceFactory:
    """
    Factory class for creating AI service instances
    """

    @staticmethod
    def create_service() -> AIServiceInterface:
        """
        Create a Gemini AI service instance

        Returns:
            AIServiceInterface: An instance of the Gemini service
        """
        return GeminiService()
