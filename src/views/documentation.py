"""Documentation view: short in-app guide."""

import streamlit as st

from src.config import get_settings
from src.ui.components import page_header


def render() -> None:
    page_header("Prompt", "Docs", "How to get the most out of each section of the app.")

    col1, col2, col3 = st.columns(3)
    with col1, st.container(border=True):
        st.markdown("##### 🎮 Playground")
        st.write(
            "Write a **system prompt** (how the model should behave) and a **user prompt** "
            "(what you ask), tune the temperature and compare answers side by side."
        )
    with col2, st.container(border=True):
        st.markdown("##### 🔐 Engage")
        st.write(
            "A prompt-injection game. Each level hides a password in the system prompt. "
            "Talk the model into revealing it, then submit your guess."
        )
    with col3, st.container(border=True):
        st.markdown("##### 🎬 Reservation")
        st.write(
            "An agent with tools. Ask it to find movies, book one, or read stored data, "
            "and inspect which tools it called."
        )

    st.markdown("#### Learn more")
    st.link_button(
        "Prompting Guide",
        get_settings().documentation_url,
        icon=":material/menu_book:",
    )
