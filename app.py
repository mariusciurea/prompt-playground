"""AI Playground - Streamlit entry point."""

import logging

import streamlit as st

from src.config import get_settings
from src.ui.components import inject_styles
from src.views import documentation, engage, playground, reservation


def main() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    st.set_page_config(
        page_title=settings.app_title,
        page_icon=settings.app_icon,
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    inject_styles()

    navigation = st.navigation(
        [
            st.Page(
                playground.render,
                title="Playground",
                icon=":material/science:",
                url_path="playground",
                default=True,
            ),
            st.Page(
                engage.render,
                title="Engage",
                icon=":material/lock:",
                url_path="engage",
            ),
            st.Page(
                reservation.render,
                title="Reservation",
                icon=":material/theaters:",
                url_path="reservation",
            ),
            st.Page(
                documentation.render,
                title="Documentation",
                icon=":material/menu_book:",
                url_path="documentation",
            ),
        ],
        position="top",
    )
    navigation.run()


main()
