"""
UI components for the AI Playground application.

This module contains reusable UI components that follow the
Single Responsibility Principle.
"""

import streamlit as st
from typing import List, Callable, Optional
from src.config import (
    UIConfig,
    StyleConfig,
    GEMINI_MODEL_NAME,
    ENGAGE_LEVELS,
)
from src.models.models import ModelResponse
from src.session_manager import SessionStateManager


class HeaderComponent:
    """Component responsible for rendering the application header."""

    @staticmethod
    def render(
        current_view: str = "playground",
        on_engage_click: Optional[Callable[[], None]] = None,
        on_playground_click: Optional[Callable[[], None]] = None,
        on_documentation_click: Optional[Callable[[], None]] = None,
    ) -> None:
        """
        Render the application header with title and navigation buttons.

        Args:
            current_view: "playground" or "engage"
            on_engage_click: Callback when Engage button is clicked
            on_playground_click: Callback when Playground button is clicked
            on_documentation_click: Callback when Documentation button is clicked
        """
        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            title = UIConfig.ENGAGE_TITLE if current_view == "engage" else UIConfig.PAGE_TITLE
            st.markdown(
                f'<div class="header-text">{title}</div>',
                unsafe_allow_html=True
            )

        with col2:
            if st.button(
                UIConfig.DOCUMENTATION_BUTTON,
                use_container_width=True,
                key="doc_button"
            ) and on_documentation_click:
                on_documentation_click()

        with col3:
            if current_view == "engage":
                btn_label = UIConfig.PLAYGROUND_BUTTON
                callback = on_playground_click
                key = "playground_button"
            else:
                btn_label = UIConfig.ENGAGE_BUTTON
                callback = on_engage_click
                key = "engage_button"

            if st.button(btn_label, use_container_width=True, key=key) and callback:
                callback()

        st.markdown("---")


class ModelLabelComponent:
    """Component for displaying the AI model name."""

    @staticmethod
    def render() -> None:
        """Render the model label."""
        st.markdown(f"**{UIConfig.MODEL_LABEL}** {GEMINI_MODEL_NAME}")


class PromptInputComponent:
    """Component for prompt input areas."""
    
    @staticmethod
    def render_system_prompt(value: str, on_change: Callable[[str], None]) -> str:
        """
        Render the system prompt input area.
        
        Args:
            value: Current system prompt value
            on_change: Callback when the prompt changes
            
        Returns:
            str: The entered system prompt
        """
        st.markdown(f"**{UIConfig.SYSTEM_PROMPT_LABEL}**")
        prompt = st.text_area(
            "System Prompt",
            value=value,
            height=150,
            placeholder=UIConfig.SYSTEM_PROMPT_PLACEHOLDER,
            label_visibility="collapsed",
            key="system_prompt_input"
        )
        
        if prompt != value:
            on_change(prompt)
        
        return prompt
    
    @staticmethod
    def render_user_prompt(value: str, on_change: Callable[[str], None]) -> str:
        """
        Render the user prompt input area.
        
        Args:
            value: Current user prompt value
            on_change: Callback when the prompt changes
            
        Returns:
            str: The entered user prompt
        """
        st.markdown(f"**{UIConfig.PROMPT_LABEL}**")
        prompt = st.text_area(
            "User Prompt",
            value=value,
            height=200,
            placeholder=UIConfig.PROMPT_PLACEHOLDER,
            label_visibility="collapsed",
            key="user_prompt_input"
        )
        
        if prompt != value:
            on_change(prompt)
        
        return prompt


class ActionButtonsComponent:
    """Component for action buttons (Reset, Submit)."""
    
    @staticmethod
    def render(on_reset: Callable[[], None], on_submit: Callable[[], None]) -> tuple[bool, bool]:
        """
        Render the action buttons.
        
        Args:
            on_reset: Callback for reset action
            on_submit: Callback for submit action
            
        Returns:
            tuple: (reset_clicked, submit_clicked)
        """
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col2:
            reset_clicked = st.button(
                UIConfig.RESET_BUTTON,
                use_container_width=True,
                key="reset_button"
            )
        
        with col3:
            submit_clicked = st.button(
                UIConfig.SUBMIT_BUTTON,
                use_container_width=True,
                type="primary",
                key="submit_button"
            )
        
        if reset_clicked:
            on_reset()
        
        if submit_clicked:
            on_submit()
        
        return reset_clicked, submit_clicked


class ResponseDisplayComponent:
    """Component for displaying model responses"""
    
    @staticmethod
    def render(
        responses: List[ModelResponse],
        show_system_prompt: bool,
        show_user_prompt: bool,
        on_toggle_system: Callable[[], None],
        on_toggle_user: Callable[[], None],
        system_prompt: str,
        user_prompt: str
    ) -> None:
        """
        Render the responses display area.
        
        Args:
            responses: List of model responses to display
            show_system_prompt: Whether to show system prompt
            show_user_prompt: Whether to show user prompt
            on_toggle_system: Callback to toggle system prompt visibility
            on_toggle_user: Callback to toggle user prompt visibility
            system_prompt: The system prompt text
            user_prompt: The user prompt text
        """
        st.markdown(f"**{UIConfig.MODEL_ANSWERS_LABEL}**")
        
        if not responses:
            st.info("No responses yet. Enter prompts and click Submit to generate responses.")
            return
        
        for idx, response in enumerate(responses):
            with st.container():
                # Response header with toggle buttons
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.markdown(f"**Response {idx + 1}** - {response.model_name}")
                
                with col2:
                    if st.button(
                        UIConfig.VIEW_PROMPT_BUTTON,
                        key=f"view_prompt_{idx}",
                        use_container_width=True
                    ):
                        on_toggle_user()
                
                with col3:
                    if st.button(
                        UIConfig.VIEW_SYSTEM_PROMPT_BUTTON,
                        key=f"view_system_{idx}",
                        use_container_width=True
                    ):
                        on_toggle_system()
                
                # Display prompts if toggled
                if show_system_prompt and system_prompt:
                    st.markdown("**System Prompt:**")
                    st.info(system_prompt)
                
                if show_user_prompt and user_prompt:
                    st.markdown("**User Prompt:**")
                    st.info(user_prompt)
                
                # Display response
                st.markdown(
                    f'<div class="answer-box">{response.response_text}</div>',
                    unsafe_allow_html=True
                )
                
                # Metadata
                if response.tokens_used:
                    st.caption(f"Tokens used: {response.tokens_used} | Generated at: {response.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
                
                st.markdown("---")


class EngageModeComponent:
    """Component for the Engage password guessing game."""

    @staticmethod
    def render(
        level: int,
        prompt_value: str,
        responses: List[ModelResponse],
        password_guess: str,
        on_level_change: Callable[[int], None],
        on_prompt_change: Callable[[str], None],
        on_reset: Callable[[], None],
        on_submit: Callable[[], None],
        on_password_guess_change: Callable[[str], None],
        on_check_password: Callable[[], None],
    ) -> None:
        """Render the full Engage game UI"""
        max_level = len(ENGAGE_LEVELS)
        left_col, right_col = st.columns([1, 1])

        with left_col:
            # Level input
            st.markdown(f"**{UIConfig.LEVEL_LABEL}**")
            new_level = st.number_input(
                "Level",
                min_value=1,
                max_value=max_level,
                value=level,
                label_visibility="collapsed",
                key="engage_level_input"
            )
            if new_level != level:
                on_level_change(int(new_level))

            st.markdown("")

            # Game instructions (green style)
            for line in UIConfig.ENGAGE_INSTRUCTIONS:
                st.markdown(
                    f'<p class="engage-instructions">{line}</p>',
                    unsafe_allow_html=True
                )

            st.markdown("")

            # Password guess section
            st.markdown(f"**{UIConfig.PASSWORD_LABEL}**")
            pwd_col1, pwd_col2 = st.columns([3, 1])
            with pwd_col1:
                guess = st.text_input(
                    "Password guess",
                    value=password_guess,
                    placeholder=UIConfig.PASSWORD_PLACEHOLDER,
                    label_visibility="collapsed",
                    key="engage_password_input"
                )
                if guess != password_guess:
                    on_password_guess_change(guess)
            with pwd_col2:
                if st.button(
                        UIConfig.CHECK_PASSWORD_BUTTON,
                        use_container_width=True,
                        key="engage_check_password_button"
                ):
                    on_check_password()

            # Prompt input
            st.markdown(f"**{UIConfig.PROMPT_LABEL}**")
            prompt = st.text_area(
                "Engage Prompt",
                value=prompt_value,
                height=200,
                placeholder=UIConfig.PROMPT_PLACEHOLDER,
                label_visibility="collapsed",
                key="engage_prompt_input"
            )
            if prompt != prompt_value:
                on_prompt_change(prompt)

            st.markdown("")

            # Reset and Submit buttons
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                if st.button(
                    UIConfig.RESET_BUTTON,
                    use_container_width=False,
                    key="engage_reset_button"
                ):
                    on_reset()
            with col3:
                if st.button(
                    UIConfig.SUBMIT_BUTTON,
                    use_container_width=True,
                    type="primary",
                    key="engage_submit_button"
                ):
                    on_submit()

            st.markdown("")

        with right_col:
            # Model answers
            st.markdown(f"**{UIConfig.MODEL_ANSWERS_LABEL}**")

            if not responses:
                st.info(
                    "No responses yet. Enter a prompt and click Submit to generate responses."
                )
            else:
                st.write(f"User prompt: {st.session_state.show_user_prompt}")
                for idx, response in enumerate(responses):
                    with st.container():
                        st.markdown(f"**Response {idx + 1}** - {response.model_name}")
                        st.markdown(
                            f'<div class="answer-box">{response.response_text}</div>',
                            unsafe_allow_html=True
                        )
                        if response.tokens_used:
                            st.caption(
                                f"Tokens used: {response.tokens_used} | "
                                f"Generated at: {response.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                            )
                        st.markdown("---")



class StyleComponent:
    """Component for injecting custom styles."""
    
    @staticmethod
    def inject_styles() -> None:
        """Inject custom CSS styles into the application."""
        st.markdown(StyleConfig.CUSTOM_CSS, unsafe_allow_html=True)
