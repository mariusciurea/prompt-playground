"""Reusable Streamlit UI building blocks."""

from collections.abc import Sequence
from datetime import datetime
from html import escape
from pathlib import Path

import streamlit as st
from streamlit.delta_generator import DeltaGenerator

from src.config import get_settings
from src.models import ModelResponse, PromptData
from src.services import AIService, AIServiceError

_STYLE_PATH = Path(__file__).with_name("style.css")
_CURSOR = " ▌"
ASSISTANT_AVATAR = "✨"


def inject_styles() -> None:
    """Inject the app stylesheet."""
    st.markdown(f"<style>{_STYLE_PATH.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def page_header(title: str, accent: str, subtitle: str, *, show_model: bool = False) -> None:
    """Render the page title (``title`` + gradient ``accent``) and a subtitle."""
    badge = ""
    if show_model:
        badge = f'<span class="model-badge">{escape(get_settings().gemini_model_name)}</span>'
    st.markdown(
        f'<p class="app-title">{escape(title)} <span class="accent">{escape(accent)}</span>'
        f"{badge}</p>"
        f'<p class="app-subtitle">{escape(subtitle)}</p>',
        unsafe_allow_html=True,
    )


def show_service_error(message: str) -> None:
    """Explain that the AI service is unavailable and how to fix it."""
    st.error(message, icon=":material/key_off:")


def stream_response(
    slot: DeltaGenerator, service: AIService, prompt: PromptData
) -> ModelResponse | None:
    """Generate a response, rendering it live inside ``slot``.

    Returns ``None`` (after showing the error) if generation failed.
    """
    with slot.container(), st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
        placeholder = st.empty()
        placeholder.markdown("_Thinking…_")
        buffer: list[str] = []

        def on_chunk(text: str) -> None:
            buffer.append(text)
            placeholder.markdown("".join(buffer) + _CURSOR)

        try:
            return service.generate_response(prompt, on_chunk)
        except AIServiceError as exc:
            placeholder.empty()
            st.error(str(exc))
            return None


def _meta_caption(response: ModelResponse) -> str:
    parts = []
    if response.tokens_used:
        parts.append(f"{response.tokens_used} tokens")
    if response.latency_seconds is not None:
        parts.append(f"{response.latency_seconds:.1f}s")
    if response.temperature is not None:
        parts.append(f"temp {response.temperature:g}")
    parts.append(response.timestamp.strftime("%H:%M:%S"))
    return " · ".join(parts)


def render_playground_response(response: ModelResponse, number: int) -> None:
    """A response with the prompts that produced it tucked into an expander."""
    with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
        st.markdown(f"**#{number} · {response.model_name}**")
        st.markdown(response.response_text)
        st.caption(_meta_caption(response))
        with st.expander("Prompts used"):
            if response.system_prompt.strip():
                st.caption("System prompt")
                st.code(response.system_prompt, language=None, wrap_lines=True)
            st.caption("User prompt")
            st.code(response.user_prompt, language=None, wrap_lines=True)


def render_conversation_turn(response: ModelResponse, number: int) -> None:
    """A user message followed by the model's answer (system prompt stays hidden)."""
    with st.chat_message("user"):
        st.caption(f"Attempt #{number}")
        st.markdown(response.user_prompt)
    with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
        st.markdown(response.response_text)
        st.caption(_meta_caption(response))


def responses_to_markdown(responses: Sequence[ModelResponse]) -> str:
    """Export a response history as a markdown document."""
    lines = [f"# AI Playground session — {datetime.now():%Y-%m-%d %H:%M}", ""]
    for number, response in enumerate(responses, start=1):
        lines += [f"## #{number} · {response.model_name}", ""]
        if response.system_prompt.strip():
            lines += ["**System prompt**", "", f"> {response.system_prompt}", ""]
        lines += ["**User prompt**", "", f"> {response.user_prompt}", ""]
        lines += [
            "**Response**",
            "",
            response.response_text,
            "",
            f"*{_meta_caption(response)}*",
            "",
        ]
    return "\n".join(lines)
