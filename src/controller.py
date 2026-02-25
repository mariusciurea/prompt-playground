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
    PromptInputComponent,
    ActionButtonsComponent,
    ResponseDisplayComponent,
    EngageModeComponent,
    ReservationChatComponent,
    StyleComponent,
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
        """on_click callback: validate, save prompt, set generating flag.

        Runs BEFORE the script body so the next render sees disabled buttons
        and a cleared text area.
        """
        user_prompt = st.session_state.get("user_prompt_input", "").strip()
        if not user_prompt:
            return
        if self._ai_service is None:
            return

        st.session_state._pending_user_prompt = user_prompt
        st.session_state._pending_system_prompt = st.session_state.get(
            "system_prompt_input", ""
        )
        self._session_manager.set_user_prompt("")
        st.session_state.user_prompt_input = ""
        self._session_manager.set_is_generating(True)

    def _process_playground_generation(self) -> None:
        """Run the actual LLM call after the UI has rendered."""
        user_prompt = st.session_state.pop("_pending_user_prompt", "")
        system_prompt = st.session_state.pop("_pending_system_prompt", "")

        if not user_prompt:
            self._session_manager.set_is_generating(False)
            return

        prompt_data = PromptData(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        try:
            with st.spinner("Generating response..."):
                response = self._ai_service.generate_response(prompt_data)
                self._session_manager.add_response(response)
        except Exception as e:
            st.error(f"Error generating response: {str(e)}")
        finally:
            self._session_manager.set_is_generating(False)
            st.rerun()
    
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

    def _on_reservation_click(self) -> None:
        """Switch to Event Reservation view."""
        self._session_manager.set_view_mode("reservation")
        st.rerun()

    def _on_documentation_click(self) -> None:
        """Switch to Documentation view."""
        self._session_manager.set_view_mode("documentation")
        st.rerun()

    # ---- Reservation agent helpers ----

    def _get_reservation_agent(self):
        """Lazily initialize the reservation agent service (cached in session state)."""
        if "reservation_agent" not in st.session_state:
            try:
                from src.agent.agent import ReservationAgentService
                st.session_state.reservation_agent = ReservationAgentService()
            except Exception as e:
                st.session_state.reservation_agent = None
                st.session_state.reservation_agent_error = str(e)
        return st.session_state.reservation_agent

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
        """on_click callback for Engage submit."""
        user_prompt = st.session_state.get("engage_prompt_input", "").strip()
        if not user_prompt:
            return
        if self._ai_service is None:
            return

        level_config = self._session_manager.get_current_level_config()
        st.session_state._pending_engage_prompt = user_prompt
        st.session_state._pending_engage_system = level_config["system_prompt"]
        self._session_manager.set_engage_prompt("")
        st.session_state.engage_prompt_input = ""
        self._session_manager.set_is_generating(True)

    def _process_engage_generation(self) -> None:
        """Run the actual LLM call for Engage mode."""
        user_prompt = st.session_state.pop("_pending_engage_prompt", "")
        system_prompt = st.session_state.pop("_pending_engage_system", "")

        if not user_prompt:
            self._session_manager.set_is_generating(False)
            return

        prompt_data = PromptData(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        try:
            with st.spinner("Generating response..."):
                response = self._ai_service.generate_response(prompt_data)
                self._session_manager.add_engage_response(response)
        except Exception as e:
            st.error(f"Error generating response: {str(e)}")
        finally:
            self._session_manager.set_is_generating(False)
            st.rerun()

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
        allowed_views = {"playground", "engage", "reservation", "documentation"}
        query_view = st.query_params.get("view")
        if isinstance(query_view, list):
            query_view = query_view[0] if query_view else None
        if query_view in allowed_views:
            self._session_manager.set_view_mode(query_view)

        view_mode = self._session_manager.get_view_mode()

        HeaderComponent.render(
            current_view=view_mode,
            on_engage_click=self._on_engage_click,
            on_playground_click=self._on_playground_click,
            on_reservation_click=self._on_reservation_click,
            on_documentation_click=self._on_documentation_click,
        )

        if view_mode == "engage":
            self._run_engage_view()
        elif view_mode == "reservation":
            self._run_reservation_view()
        elif view_mode == "documentation":
            self._run_documentation_view()
        else:
            self._run_playground_view()

    def _run_engage_view(self) -> None:
        """Render the Engage game view."""
        is_generating = self._session_manager.get_is_generating()

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
            disabled=is_generating,
        )

        if is_generating:
            self._process_engage_generation()

    def _run_reservation_view(self) -> None:
        """Render the Event Reservation chat view."""
        agent = self._get_reservation_agent()

        if agent is None:
            error = st.session_state.get("reservation_agent_error", "Unknown error")
            st.error(f"Could not initialize reservation agent: {error}")
            return

        ReservationChatComponent.render(
            self._session_manager.get_reservation_messages()
        )

        user_input = st.chat_input("Type your message...")
        if user_input:
            self._session_manager.add_reservation_message("user", user_input)
            with st.chat_message("user"):
                st.markdown(user_input)

            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    try:
                        reply = agent.send_message(user_input)
                    except Exception as e:
                        reply = f"Error: {e}"
                    st.markdown(reply)

            self._session_manager.add_reservation_message("assistant", reply)
            st.rerun()

    def _run_playground_view(self) -> None:
        """Render the main Playground view."""
        is_generating = self._session_manager.get_is_generating()

        left_col, mid_col, right_col = st.columns([50, 1, 50])

        with mid_col:
            st.markdown('<div class="col-divider"></div>', unsafe_allow_html=True)

        # Left column - Input section
        with left_col:
            if self._ai_service_error:
                st.error(self._ai_service_error)

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
                on_submit=self._on_submit,
                disabled=is_generating,
            )
        
        # Right column - Response section
        with right_col:
            ResponseDisplayComponent.render(
                responses=self._session_manager.get_responses(),
                show_user_prompt=self._session_manager.get_show_user_prompt(),
                on_toggle_user=self._on_toggle_user_prompt,
            )

        if is_generating:
            self._process_playground_generation()

    def _run_documentation_view(self) -> None:
        """Render in-app documentation."""
        st.markdown("### Documentation")
        st.markdown(
            "Use the navigation links above to switch between `Playground`, "
            "`Engage`, and `Reservation`."
        )
        st.markdown(
            "- `Playground`: test prompts with a system prompt and user prompt.\n"
            "- `Engage`: practice prompt-injection scenarios by guessing passwords.\n"
            "- `Reservation`: chat with the event reservation assistant."
        )


def create_controller() -> PlaygroundController:
    """
    Factory function to create a PlaygroundController instance.
    
    Returns:
        PlaygroundController: A new controller instance
    """
    return PlaygroundController()
