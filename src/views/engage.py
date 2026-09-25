"""Engage view: a prompt-injection game where the goal is to extract a password."""

import streamlit as st

from src.config import get_settings
from src.engage import ENGAGE_INSTRUCTIONS, ENGAGE_LEVELS
from src.models import PromptData
from src.state import EngageState, engage_state, get_ai_service
from src.ui.components import (
    page_header,
    render_conversation_turn,
    show_service_error,
    stream_response,
)

LEVEL_KEY = "engage_level"
PROMPT_KEY = "engage_prompt"
GUESS_KEY = "engage_guess"


def _level_label(level: int) -> str:
    return f"Level {level} ✅" if level in engage_state().solved else f"Level {level}"


def _current_level(state: EngageState) -> int:
    """Read the level selector; segmented controls can be deselected, so fall back."""
    selected = st.session_state.get(LEVEL_KEY)
    state.level = selected or state.level
    return state.level


def _go_to_level(level: int) -> None:
    st.session_state[LEVEL_KEY] = level
    engage_state().level = level


def _check_password() -> None:
    state = engage_state()
    guess = st.session_state[GUESS_KEY].strip()
    if not guess:
        state.feedback = ("warning", "Please enter a password guess.")
    elif ENGAGE_LEVELS[state.level - 1].is_correct(guess):
        state.solved.add(state.level)
        state.feedback = ("success", "Congratulations! You guessed the password correctly!")
        st.session_state[GUESS_KEY] = ""
    else:
        state.feedback = ("error", "Wrong password. Keep trying!")


def _reset_level() -> None:
    state = engage_state()
    state.responses.pop(state.level, None)
    state.solved.discard(state.level)
    st.session_state[PROMPT_KEY] = ""
    st.session_state[GUESS_KEY] = ""


def _render_feedback(state: EngageState) -> None:
    if not state.feedback:
        return
    kind, message = state.feedback
    state.feedback = None
    getattr(st, kind)(message)
    if kind == "success":
        st.balloons()


def _render_play_column(state: EngageState, level: int) -> bool:
    """Render the input column and return whether a message was sent."""
    st.info("  \n".join(ENGAGE_INSTRUCTIONS), icon=":material/lock:")

    with st.form("engage_prompt_form", border=False):
        st.text_area(
            "Your message",
            key=PROMPT_KEY,
            height=160,
            max_chars=get_settings().max_prompt_length,
            placeholder="Try to make the assistant reveal the password…",
        )
        sent = st.form_submit_button(
            "Send",
            type="primary",
            icon=":material/send:",
            width="stretch",
            disabled=get_ai_service()[0] is None,
            help="Ctrl + Enter also submits.",
        )

    st.markdown("##### Got it?")
    with st.form("engage_guess_form", border=False, clear_on_submit=False):
        st.text_input(
            "Password",
            key=GUESS_KEY,
            placeholder="Enter your guess…",
            label_visibility="collapsed",
        )
        st.form_submit_button(
            "Check password",
            icon=":material/key:",
            width="stretch",
            on_click=_check_password,
        )
    _render_feedback(state)

    if level in state.solved and level < len(ENGAGE_LEVELS):
        st.button(
            "Next level",
            icon=":material/arrow_forward:",
            type="primary",
            on_click=_go_to_level,
            args=(level + 1,),
        )
    st.button(
        "Reset this level",
        icon=":material/restart_alt:",
        on_click=_reset_level,
        type="tertiary",
    )
    return sent


def _render_answers_column(state: EngageState, level: int, *, sent: bool) -> None:
    st.markdown("#### Model answers")
    history = state.responses.setdefault(level, [])
    live = st.empty()

    if sent:
        message = st.session_state[PROMPT_KEY]
        service, _ = get_ai_service()
        if not message.strip():
            st.warning("Write a message first.", icon=":material/edit:")
        elif service:
            response = stream_response(
                live,
                service,
                PromptData(
                    system_prompt=ENGAGE_LEVELS[level - 1].system_prompt,
                    user_prompt=message,
                ),
            )
            if response:
                history.append(response)
                live.empty()

    if not history:
        st.info("No answers yet. Send a message to start.", icon=":material/chat:")
        return
    for number, response in reversed(list(enumerate(history, start=1))):
        render_conversation_turn(response, number)


def render() -> None:
    state = engage_state()
    st.session_state.setdefault(LEVEL_KEY, state.level)
    st.session_state.setdefault(PROMPT_KEY, "")
    st.session_state.setdefault(GUESS_KEY, "")

    page_header("Prompt", "Engage", "Trick the model into revealing its secret password.")
    _, error = get_ai_service()
    if error:
        show_service_error(error)

    total = len(ENGAGE_LEVELS)
    st.progress(len(state.solved) / total, text=f"{len(state.solved)} of {total} levels cleared")
    st.segmented_control(
        "Level",
        range(1, total + 1),
        key=LEVEL_KEY,
        format_func=_level_label,
        label_visibility="collapsed",
    )
    level = _current_level(state)

    left, right = st.columns(2, gap="large")
    with left:
        sent = _render_play_column(state, level)
    with right:
        _render_answers_column(state, level, sent=sent)
