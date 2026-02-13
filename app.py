"""
AI Playground - Main Application Entry Point
"""

import streamlit as st
from src.config import UIConfig
from src.controller import create_controller

from dotenv import load_dotenv


load_dotenv()


def configure_page() -> None:
    """Configure the Streamlit page settings."""
    st.set_page_config(
        page_title=UIConfig.PAGE_TITLE,
        page_icon=UIConfig.PAGE_ICON,
        layout=UIConfig.LAYOUT,
        initial_sidebar_state="collapsed"
    )


def main() -> None:
    """
    Main application entry point.
    
    This function initializes and runs the AI Playground application.
    """
    # Configure page
    configure_page()
    
    # Create and run controller
    controller = create_controller()
    controller.run()


if __name__ == "__main__":
    main()
