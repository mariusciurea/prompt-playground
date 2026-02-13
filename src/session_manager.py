"""
Session state management for the AI Playground application
"""

import streamlit as st
from typing import Any, List
from src.models.models import ModelResponse
from src.config import AppConfig, ENGAGE_LEVELS


class SessionStateManager:
    """
    Manages Streamlit session state for the application.
    
    Responsibilities:
    - Initialize session state variables
    - Provide getter/setter methods for state variables
    - Handle state reset operations
    """
    
    def __init__(self):
        """Initialize the session state manager."""
        self._initialize_state()

    @staticmethod
    def _initialize_state() -> None:
        """Initialize all session state variables if they don't exist."""
        if "system_prompt" not in st.session_state:
            st.session_state.system_prompt = ""
        
        if "user_prompt" not in st.session_state:
            st.session_state.user_prompt = ""

        if "responses" not in st.session_state:
            st.session_state.responses = []
        
        if "show_system_prompt" not in st.session_state:
            st.session_state.show_system_prompt = False
        
        if "show_user_prompt" not in st.session_state:
            st.session_state.show_user_prompt = False

        # View mode: "playground" (default) or "engage"
        if "view_mode" not in st.session_state:
            st.session_state.view_mode = "playground"

        # Engage game state
        if "engage_level" not in st.session_state:
            st.session_state.engage_level = 1
        if "engage_prompt" not in st.session_state:
            st.session_state.engage_prompt = ""
        if "engage_responses" not in st.session_state:
            st.session_state.engage_responses = []
        if "engage_password_guess" not in st.session_state:
            st.session_state.engage_password_guess = ""

    @staticmethod
    def get_system_prompt() -> str:
        """Get the current system prompt from session state."""
        return st.session_state.system_prompt

    @staticmethod
    def set_system_prompt(prompt: str) -> None:
        """Set the system prompt in session state."""
        st.session_state.system_prompt = prompt

    @staticmethod
    def get_user_prompt() -> str:
        """Get the current user prompt from session state."""
        return st.session_state.user_prompt

    @staticmethod
    def set_user_prompt(prompt: str) -> None:
        """Set the user prompt in session state."""
        st.session_state.user_prompt = prompt

    @staticmethod
    def get_responses() -> List[ModelResponse]:
        """Get all model responses from session state."""
        return st.session_state.responses

    @staticmethod
    def add_response(response: ModelResponse) -> None:
        """Add a new response to the session state."""
        st.session_state.responses.append(response)

    @staticmethod
    def clear_responses() -> None:
        """Clear all responses from session state."""
        st.session_state.responses = []

    @staticmethod
    def reset_all() -> None:
        """Reset all session state to default values."""
        st.session_state.system_prompt = ""
        st.session_state.user_prompt = ""
        st.session_state.responses = []
        st.session_state.show_system_prompt = False
        st.session_state.show_user_prompt = False

    @staticmethod
    def toggle_system_prompt_view() -> None:
        """Toggle the visibility of the system prompt in responses."""
        st.session_state.show_system_prompt = not st.session_state.show_system_prompt

    @staticmethod
    def toggle_user_prompt_view() -> None:
        """Toggle the visibility of the user prompt in responses."""
        st.session_state.show_user_prompt = not st.session_state.show_user_prompt

    @staticmethod
    def get_show_system_prompt() -> bool:
        """Check if system prompt should be shown in responses."""
        return st.session_state.show_system_prompt

    @staticmethod
    def get_show_user_prompt() -> bool:
        """Check if user prompt should be shown in responses."""
        return st.session_state.show_user_prompt

    @staticmethod
    def get_view_mode() -> str:
        """Get current view mode (playground or engage)."""
        return st.session_state.view_mode

    @staticmethod
    def set_view_mode(mode: str) -> None:
        """Set view mode."""
        st.session_state.view_mode = mode

    @staticmethod
    def get_engage_level() -> int:
        """Get current engage game level."""
        return st.session_state.engage_level

    @staticmethod
    def set_engage_level(level: int) -> None:
        """Set engage game level."""
        max_level = len(ENGAGE_LEVELS)
        st.session_state.engage_level = max(1, min(level, max_level))

    @staticmethod
    def get_engage_prompt() -> str:
        """Get engage game user prompt."""
        return st.session_state.engage_prompt

    @staticmethod
    def set_engage_prompt(prompt: str) -> None:
        """Set engage game user prompt."""
        st.session_state.engage_prompt = prompt

    @staticmethod
    def get_engage_responses() -> List[ModelResponse]:
        """Get engage game responses."""
        return st.session_state.engage_responses

    @staticmethod
    def add_engage_response(response: ModelResponse) -> None:
        """Add response to engage game."""
        st.session_state.engage_responses.append(response)

    @staticmethod
    def get_engage_password_guess() -> str:
        """Get user's password guess."""
        return st.session_state.engage_password_guess

    @staticmethod
    def set_engage_password_guess(guess: str) -> None:
        """Set user's password guess."""
        st.session_state.engage_password_guess = guess

    @staticmethod
    def reset_engage_game() -> None:
        """Reset engage game state for current level."""
        st.session_state.engage_prompt = ""
        st.session_state.engage_responses = []
        st.session_state.engage_password_guess = ""

    @staticmethod
    def get_current_level_config() -> dict:
        """Get config for current engage level."""
        idx = st.session_state.engage_level - 1
        return ENGAGE_LEVELS[idx]
