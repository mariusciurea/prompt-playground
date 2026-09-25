"""Playground view: experiment with system + user prompts."""

import streamlit as st

from src.config import get_settings
from src.models import ModelResponse, PromptData
from src.state import get_ai_service, playground_state
from src.ui.components import (
    page_header,
    render_playground_response,
    responses_to_markdown,
    show_service_error,
    stream_response,
)

SYSTEM_KEY = "playground_system_prompt"
USER_KEY = "playground_user_prompt"
TEMPERATURE_KEY = "playground_temperature"
EXAMPLE_KEY = "playground_example"

EXAMPLES: dict[str, tuple[str, str]] = {
    "🌍 Translator": (
        "You are a professional translator. Translate the user's text into French, "
        "preserving tone and register. Reply with the translation only.",
        "The quick brown fox jumps over the lazy dog.",
    ),
    "🏴‍☠️ Pirate": (
        "You are a pirate captain. Answer everything in pirate speak, "
        "with plenty of nautical metaphors.",
        "How do I make a good cup of coffee?",
    ),
    "🧑‍💻 Code reviewer": (
        "You are a senior Python reviewer. Point out bugs first, then style issues. Be concise.",
        "def add(a, b):\n    return a - b\n\nprint(add(2, 3))",
    ),
    "📝 Summarizer": (
        "Summarize the user's text in exactly three bullet points.",
        "Large language models are trained on vast text corpora to predict the next token. "
        "Prompt engineering is the practice of crafting inputs that steer the model toward "
        "useful, accurate and safe outputs, using techniques like few-shot examples, "
        "role prompting and chain-of-thought reasoning.",
    ),
    "🔎 JSON extractor": (
        "Extract entities from the text and answer with valid JSON only, using the keys "
        '"people", "places" and "dates".',
        "Ada Lovelace met Charles Babbage in London on 5 June 1833.",
    ),
}


def _init_state() -> None:
    st.session_state.setdefault(SYSTEM_KEY, "")
    st.session_state.setdefault(USER_KEY, "")
    st.session_state.setdefault(TEMPERATURE_KEY, get_settings().default_temperature)


def _load_example() -> None:
    choice = st.session_state.get(EXAMPLE_KEY)
    if choice:
        st.session_state[SYSTEM_KEY], st.session_state[USER_KEY] = EXAMPLES[choice]


def _clear_inputs() -> None:
    st.session_state[SYSTEM_KEY] = ""
    st.session_state[USER_KEY] = ""
    st.session_state[EXAMPLE_KEY] = None


def _clear_history() -> None:
    playground_state().responses.clear()


def _render_inputs(*, can_submit: bool) -> bool:
    """Render the input column and return whether Run was pressed."""
    max_chars = get_settings().max_prompt_length

    st.pills(
        "Start from an example",
        list(EXAMPLES),
        key=EXAMPLE_KEY,
        on_change=_load_example,
        help="Loads a ready-made system + user prompt you can then tweak.",
    )
    with st.form("playground_form", border=False):
        st.text_area(
            "System prompt",
            key=SYSTEM_KEY,
            height=130,
            max_chars=max_chars,
            placeholder="How should the model behave? (optional)",
        )
        st.text_area(
            "User prompt",
            key=USER_KEY,
            height=180,
            max_chars=max_chars,
            placeholder="What do you want to ask?",
        )
        with st.expander("Generation settings"):
            st.slider(
                "Temperature",
                0.0,
                2.0,
                step=0.1,
                key=TEMPERATURE_KEY,
                help="Lower is more deterministic, higher is more creative.",
            )
        submitted = st.form_submit_button(
            "Run",
            type="primary",
            icon=":material/play_arrow:",
            width="stretch",
            disabled=not can_submit,
            help="Ctrl + Enter also submits.",
        )
    st.button(
        "Clear prompts",
        icon=":material/backspace:",
        on_click=_clear_inputs,
        type="tertiary",
    )
    return submitted


def _render_toolbar(responses: list[ModelResponse]) -> None:
    header, download, clear = st.columns([3, 1, 1], vertical_alignment="center")
    header.markdown("#### Model answers")
    if responses:
        download.download_button(
            "Export",
            responses_to_markdown(responses),
            file_name="playground_session.md",
            mime="text/markdown",
            icon=":material/download:",
            width="stretch",
        )
        clear.button(
            "Clear",
            icon=":material/delete:",
            on_click=_clear_history,
            width="stretch",
        )


def _render_results(service, *, submitted: bool) -> None:
    state = playground_state()
    toolbar = st.container()  # filled after generation so it reflects the new response
    live = st.empty()
    if submitted:
        user_prompt = st.session_state[USER_KEY]
        if not user_prompt.strip():
            st.warning("Write a user prompt first.", icon=":material/edit:")
        else:
            response = stream_response(
                live,
                service,
                PromptData(
                    system_prompt=st.session_state[SYSTEM_KEY],
                    user_prompt=user_prompt,
                    temperature=st.session_state[TEMPERATURE_KEY],
                ),
            )
            if response:
                state.responses.append(response)
                live.empty()
                st.toast("Response ready", icon=":material/check_circle:")

    with toolbar:
        _render_toolbar(state.responses)

    if not state.responses:
        st.info("No responses yet. Write a prompt and press **Run**.", icon=":material/chat:")
        return
    total = len(state.responses)
    for offset, response in enumerate(reversed(state.responses)):
        render_playground_response(response, total - offset)


def render() -> None:
    _init_state()
    page_header(
        "AI",
        "Playground",
        "Experiment with system and user prompts and compare the answers.",
        show_model=True,
    )
    service, error = get_ai_service()
    if error:
        show_service_error(error)

    left, right = st.columns(2, gap="large")
    with left:
        submitted = _render_inputs(can_submit=service is not None)
    with right:
        _render_results(service, submitted=submitted)
