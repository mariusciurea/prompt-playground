"""Reservation view: chat with the cinema reservation agent."""

import streamlit as st

from src.agent.agent import AgentError, ToolCall
from src.state import ChatMessage, get_reservation_agent, reservation_state
from src.ui.components import page_header, show_service_error

PENDING_KEY = "_reservation_pending_prompt"

SUGGESTIONS = (
    "What movies are on tomorrow at 19:00?",
    "Book me a thriller for Saturday at 8 PM",
    "Show me the stored cinema information",
)


def _queue_prompt(prompt: str) -> None:
    st.session_state[PENDING_KEY] = prompt


def _new_conversation() -> None:
    reservation_state().messages.clear()
    agent, _ = get_reservation_agent()
    if agent:
        agent.reset_session()


def _render_tool_calls(tool_calls: list[ToolCall]) -> None:
    if not tool_calls:
        return
    with st.expander(f"Used {len(tool_calls)} tool(s)", icon=":material/build:"):
        for call in tool_calls:
            st.markdown(f"**`{call.name}`**")
            st.json({"arguments": call.args, "result": call.result}, expanded=False)


def _render_content(message: ChatMessage) -> None:
    st.markdown(message.content)
    _render_tool_calls(message.tool_calls)


def _render_message(message: ChatMessage) -> None:
    with st.chat_message(message.role):
        _render_content(message)


def render() -> None:
    page_header(
        "Event", "Reservation", "Chat with an AI agent that can book movies and read stored data."
    )

    agent, error = get_reservation_agent()
    if agent is None:
        show_service_error(f"Could not initialize the reservation agent: {error}")
        return

    state = reservation_state()
    st.button(
        "New conversation",
        icon=":material/add_comment:",
        on_click=_new_conversation,
        type="tertiary",
        disabled=not state.messages,
    )
    for message in state.messages:
        _render_message(message)

    suggestions = st.empty()
    if not state.messages:
        with suggestions.container():
            st.markdown("##### Try asking…")
            for suggestion in SUGGESTIONS:
                st.button(
                    suggestion,
                    key=f"suggestion_{suggestion}",
                    on_click=_queue_prompt,
                    args=(suggestion,),
                )

    prompt = st.chat_input("Type your message…") or st.session_state.pop(PENDING_KEY, None)
    if not prompt:
        return

    suggestions.empty()
    user_message = ChatMessage("user", prompt)
    _render_message(user_message)
    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            try:
                reply = agent.send_message(prompt)
            except AgentError as exc:
                st.error(str(exc))
                return
        assistant_message = ChatMessage("assistant", reply.text, reply.tool_calls)
        _render_content(assistant_message)
    state.messages += [user_message, assistant_message]
