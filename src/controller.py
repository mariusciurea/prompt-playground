"""
Application controller module.

This module contains the main application controller that orchestrates
the interaction between UI components, session management, and AI services.
"""

from typing import Optional
from src.session_manager import SessionStateManager
from src.ai_service import AIServiceFactory, AIServiceInterface
from src.models.models import PromptData, ModelResponse
from src.config import UIConfig
from src.ui_components import (
    HeaderComponent,
    ModelLabelComponent,
    PromptInputComponent,
    ActionButtonsComponent,
    ResponseDisplayComponent,
    EngageModeComponent,
    StyleComponent
)
import streamlit as st


class PlaygroundController:
    """
    Main controller for the AI Playground application.
    
    Responsibilities:
    - Coordinate interactions between UI and business logic
    - Handle user actions and events
    - Manage the application flow
    """
    
    def __init__(self):
        """Initialize the playground controller."""
        self._session_manager = SessionStateManager()
        self._ai_service: Optional[AIServiceInterface] = None
        self._ai_service_error: Optional[str] = None
        self._initialize_ai_service()
    
    def _initialize_ai_service(self) -> None:
        """Initialize the Gemini AI service."""
        try:
            self._ai_service = AIServiceFactory.create_service()
        except ValueError as e:
            self._ai_service = None
            self._ai_service_error = str(e)
        else:
            self._ai_service_error = None

    def _on_system_prompt_change(self, prompt: str) -> None:
        """
        Handle system prompt change.
        
        Args:
            prompt: The new system prompt text
        """
        self._session_manager.set_system_prompt(prompt)
    
    def _on_user_prompt_change(self, prompt: str) -> None:
        """
        Handle user prompt change.
        
        Args:
            prompt: The new user prompt text
        """
        self._session_manager.set_user_prompt(prompt)
    
    def _on_reset(self) -> None:
        """Handle reset button click."""
        self._session_manager.reset_all()
        st.rerun()
    
    def _on_submit(self) -> None:
        """Handle submit button click."""
        system_prompt = self._session_manager.get_system_prompt()
        user_prompt = self._session_manager.get_user_prompt()
        
        if self._ai_service is None and self._ai_service_error:
            st.error(self._ai_service_error)
            return

        if not user_prompt.strip():
            st.warning("Please enter a user prompt before submitting.")
            return

        # Create prompt data
        prompt_data = PromptData(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )
        
        # Generate response
        try:
            with st.spinner("Generating response..."):
                response = self._ai_service.generate_response(prompt_data)
                self._session_manager.add_response(response)
            
            st.success("Response generated successfully!")
        except Exception as e:
            st.error(f"Error generating response: {str(e)}")
    
    def _on_toggle_system_prompt(self) -> None:
        """Handle toggle system prompt visibility."""
        self._session_manager.toggle_system_prompt_view()
    
    def _on_toggle_user_prompt(self) -> None:
        """Handle toggle user prompt visibility."""
        self._session_manager.toggle_user_prompt_view()

    def _on_engage_click(self) -> None:
        """Switch to Engage game view."""
        self._session_manager.set_view_mode("engage")
        st.rerun()

    def _on_playground_click(self) -> None:
        """Switch to Playground view."""
        self._session_manager.set_view_mode("playground")
        st.rerun()

    def _on_engage_level_change(self, level: int) -> None:
        """Handle engage level change."""
        self._session_manager.set_engage_level(level)
        self._session_manager.reset_engage_game()
        st.rerun()

    def _on_engage_prompt_change(self, prompt: str) -> None:
        """Handle engage prompt change."""
        self._session_manager.set_engage_prompt(prompt)

    def _on_engage_reset(self) -> None:
        """Reset engage game."""
        self._session_manager.reset_engage_game()
        st.rerun()

    def _on_engage_submit(self) -> None:
        """Submit prompt in Engage game."""
        if self._ai_service is None and self._ai_service_error:
            st.error(self._ai_service_error)
            return

        user_prompt = self._session_manager.get_engage_prompt()
        if not user_prompt.strip():
            st.warning("Please enter a prompt before submitting.")
            return

        level_config = self._session_manager.get_current_level_config()
        prompt_data = PromptData(
            system_prompt=level_config["system_prompt"],
            user_prompt=user_prompt
        )

        try:
            with st.spinner("Generating response..."):
                response = self._ai_service.generate_response(prompt_data)
                self._session_manager.add_engage_response(response)
            st.success("Response generated successfully!")
        except Exception as e:
            st.error(f"Error generating response: {str(e)}")

    def _on_engage_password_guess_change(self, guess: str) -> None:
        """Handle password guess change."""
        self._session_manager.set_engage_password_guess(guess)

    def _on_check_password(self) -> None:
        """Check if password guess is correct."""
        guess = self._session_manager.get_engage_password_guess().strip()
        if not guess:
            st.warning("Please enter a password guess.")
            return

        level_config = self._session_manager.get_current_level_config()
        correct_password = level_config["password"]

        if guess.lower() == correct_password.lower():
            st.info(UIConfig.PASSWORD_CORRECT_MSG)
        else:
            st.error(UIConfig.PASSWORD_INCORRECT_MSG)

    def _on_engage_toggle_user_prompt(self) -> None:
        """Toggle user prompt visibility in engage responses."""
        self._session_manager.toggle_engage_user_prompt_view()

    def run(self) -> None:
        """Run the main application loop."""
        StyleComponent.inject_styles()

        view_mode = self._session_manager.get_view_mode()

        # render header with view switching
        HeaderComponent.render(
            current_view=view_mode,
            on_engage_click=self._on_engage_click,
            on_playground_click=self._on_playground_click,
        )

        if view_mode == "engage":
            self._run_engage_view()
        else:
            self._run_playground_view()

    def _run_engage_view(self) -> None:
        """Render the Engage game view."""
        EngageModeComponent.render(
            level=self._session_manager.get_engage_level(),
            prompt_value=self._session_manager.get_engage_prompt(),
            responses=self._session_manager.get_engage_responses(),
            password_guess=self._session_manager.get_engage_password_guess(),
            show_user_prompt=self._session_manager.get_engage_show_user_prompt(),
            on_level_change=self._on_engage_level_change,
            on_prompt_change=self._on_engage_prompt_change,
            on_reset=self._on_engage_reset,
            on_submit=self._on_engage_submit,
            on_password_guess_change=self._on_engage_password_guess_change,
            on_check_password=self._on_check_password,
            on_toggle_user_prompt=self._on_engage_toggle_user_prompt,
        )

    def _run_playground_view(self) -> None:
        """Render the main Playground view."""
        left_col, right_col = st.columns([1, 1])
        
        # Left column - Input section
        with left_col:
            if self._ai_service_error:
                st.error(self._ai_service_error)

            ModelLabelComponent.render()

            st.markdown("")  # Spacing

            # System prompt input
            PromptInputComponent.render_system_prompt(
                value=self._session_manager.get_system_prompt(),
                on_change=self._on_system_prompt_change
            )
            
            st.markdown("")  # Spacing
            
            # User prompt input
            PromptInputComponent.render_user_prompt(
                value=self._session_manager.get_user_prompt(),
                on_change=self._on_user_prompt_change
            )
            
            st.markdown("")  # Spacing
            
            # Action buttons
            ActionButtonsComponent.render(
                on_reset=self._on_reset,
                on_submit=self._on_submit
            )
        
        # Right column - Response section
        with right_col:
            ResponseDisplayComponent.render(
                responses=self._session_manager.get_responses(),
                show_system_prompt=self._session_manager.get_show_system_prompt(),
                show_user_prompt=self._session_manager.get_show_user_prompt(),
                on_toggle_system=self._on_toggle_system_prompt,
                on_toggle_user=self._on_toggle_user_prompt,
            )


def create_controller() -> PlaygroundController:
    """
    Factory function to create a PlaygroundController instance.
    
    Returns:
        PlaygroundController: A new controller instance
    """
    return PlaygroundController()
