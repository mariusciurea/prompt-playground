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


class HeaderComponent:
    """Component responsible for rendering the application header."""

    @staticmethod
    def render(
        current_view: str = "playground",
        on_engage_click: Optional[Callable[[], None]] = None,
        on_playground_click: Optional[Callable[[], None]] = None,
        on_documentation_click: Optional[Callable[[], None]] = None,
    ) -> None:
        """Render the application header with title and navigation."""
        col_title, col_spacer, col_doc, col_nav = st.columns([3, 1, 1, 1])

        with col_title:
            if current_view == "engage":
                st.markdown(
                    '<p class="app-title"><span class="accent">Engage</span></p>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<p class="app-title">AI <span class="accent">Playground</span></p>',
                    unsafe_allow_html=True,
                )

        with col_doc:
            if st.button(
                UIConfig.DOCUMENTATION_BUTTON,
                use_container_width=True,
                key="doc_button",
            ) and on_documentation_click:
                on_documentation_click()

        with col_nav:
            if current_view == "engage":
                if st.button(
                    UIConfig.PLAYGROUND_BUTTON,
                    use_container_width=True,
                    key="playground_button",
                ) and on_playground_click:
                    on_playground_click()
            else:
                if st.button(
                    UIConfig.ENGAGE_BUTTON,
                    use_container_width=True,
                    key="engage_button",
                ) and on_engage_click:
                    on_engage_click()

        st.markdown("---")


class ModelLabelComponent:
    """Component for displaying the AI model name."""

    @staticmethod
    def render() -> None:
        st.markdown(
            f'<p class="section-label">{UIConfig.MODEL_LABEL}</p>',
            unsafe_allow_html=True,
        )
        st.markdown(f"**{GEMINI_MODEL_NAME}**")


class PromptInputComponent:
    """Component for prompt input areas."""

    @staticmethod
    def render_system_prompt(value: str, on_change: Callable[[str], None]) -> str:
        st.markdown(
            f'<p class="section-label">{UIConfig.SYSTEM_PROMPT_LABEL}</p>',
            unsafe_allow_html=True,
        )
        prompt = st.text_area(
            "System Prompt",
            value=value,
            height=130,
            placeholder=UIConfig.SYSTEM_PROMPT_PLACEHOLDER,
            label_visibility="collapsed",
            key="system_prompt_input",
        )
        if prompt != value:
            on_change(prompt)
        return prompt

    @staticmethod
    def render_user_prompt(value: str, on_change: Callable[[str], None]) -> str:
        st.markdown(
            f'<p class="section-label">{UIConfig.PROMPT_LABEL}</p>',
            unsafe_allow_html=True,
        )
        prompt = st.text_area(
            "User Prompt",
            value=value,
            height=180,
            placeholder=UIConfig.PROMPT_PLACEHOLDER,
            label_visibility="collapsed",
            key="user_prompt_input",
        )
        if prompt != value:
            on_change(prompt)
        return prompt


class ActionButtonsComponent:
    """Component for action buttons (Reset, Submit)."""

    @staticmethod
    def render(
        on_reset: Callable[[], None], on_submit: Callable[[], None]
    ) -> tuple[bool, bool]:
        col1, col2, col3 = st.columns([2, 1, 1])
        with col2:
            reset_clicked = st.button(
                UIConfig.RESET_BUTTON,
                use_container_width=True,
                key="reset_button",
            )
        with col3:
            submit_clicked = st.button(
                UIConfig.SUBMIT_BUTTON,
                use_container_width=True,
                type="primary",
                key="submit_button",
            )
        if reset_clicked:
            on_reset()
        if submit_clicked:
            on_submit()
        return reset_clicked, submit_clicked


class ResponseDisplayComponent:
    """Component for displaying model responses."""

    @staticmethod
    def render(
        responses: List[ModelResponse],
        show_system_prompt: bool,
        show_user_prompt: bool,
        on_toggle_system: Callable[[], None],
        on_toggle_user: Callable[[], None],
    ) -> None:
        # Header row: label + two toggle buttons
        label_col, btn_col1, btn_col2 = st.columns([2.5, 1, 1])

        with label_col:
            st.markdown(
                f'<p class="section-label">{UIConfig.MODEL_ANSWERS_LABEL}</p>',
                unsafe_allow_html=True,
            )

        with btn_col1:
            if responses:
                user_label = ("Hide Prompt" if show_user_prompt
                              else UIConfig.VIEW_PROMPT_BUTTON)
                if st.button(
                    user_label,
                    use_container_width=True,
                    key="toggle_view_prompt",
                ):
                    on_toggle_user()

        with btn_col2:
            if responses:
                sys_label = ("Hide System" if show_system_prompt
                             else UIConfig.VIEW_SYSTEM_PROMPT_BUTTON)
                if st.button(
                    sys_label,
                    use_container_width=True,
                    key="toggle_view_system",
                ):
                    on_toggle_system()

        if not responses:
            st.info(
                "No responses yet. Enter prompts and click Submit to generate responses."
            )
            return

        # Responses list
        for idx, response in enumerate(responses):
            with st.container():
                st.markdown(
                    f'<span class="response-badge">#{idx + 1}</span> '
                    f"**{response.model_name}**",
                    unsafe_allow_html=True,
                )

                if show_system_prompt and response.system_prompt:
                    st.markdown(
                        f'<div class="prompt-preview"><strong>System Prompt</strong><br/>{response.system_prompt}</div>',
                        unsafe_allow_html=True,
                    )

                if show_user_prompt and response.user_prompt:
                    st.markdown(
                        f'<div class="prompt-preview"><strong>User Prompt</strong><br/>{response.user_prompt}</div>',
                        unsafe_allow_html=True,
                    )

                st.markdown(
                    f'<div class="answer-card">{response.response_text}</div>',
                    unsafe_allow_html=True,
                )

                if response.tokens_used:
                    st.markdown(
                        f'<p class="meta-caption">Tokens: {response.tokens_used} &middot; '
                        f'{response.timestamp.strftime("%Y-%m-%d %H:%M:%S")}</p>',
                        unsafe_allow_html=True,
                    )

                st.markdown("---")


class EngageModeComponent:
    """Component for the Engage password guessing game."""

    @staticmethod
    def render(
        level: int,
        prompt_value: str,
        responses: List[ModelResponse],
        password_guess: str,
        show_user_prompt: bool,
        on_level_change: Callable[[int], None],
        on_prompt_change: Callable[[str], None],
        on_reset: Callable[[], None],
        on_submit: Callable[[], None],
        on_password_guess_change: Callable[[str], None],
        on_check_password: Callable[[], None],
        on_toggle_user_prompt: Callable[[], None],
    ) -> None:
        """Render the full Engage game UI."""
        max_level = len(ENGAGE_LEVELS)
        left_col, right_col = st.columns([1, 1], gap="large")

        # ---- LEFT COLUMN ----
        with left_col:
            # Level
            st.markdown(
                f'<p class="section-label">{UIConfig.LEVEL_LABEL}</p>',
                unsafe_allow_html=True,
            )
            new_level = st.number_input(
                "Level",
                min_value=1,
                max_value=max_level,
                value=level,
                label_visibility="collapsed",
                key="engage_level_input",
            )
            if new_level != level:
                on_level_change(int(new_level))

            # Instructions
            instructions_html = "<br/>".join(UIConfig.ENGAGE_INSTRUCTIONS)
            st.markdown(
                f'<div class="engage-hint">{instructions_html}</div>',
                unsafe_allow_html=True,
            )

            # Prompt
            st.markdown(
                f'<p class="section-label">{UIConfig.PROMPT_LABEL}</p>',
                unsafe_allow_html=True,
            )
            prompt = st.text_area(
                "Engage Prompt",
                value=prompt_value,
                height=180,
                placeholder=UIConfig.PROMPT_PLACEHOLDER,
                label_visibility="collapsed",
                key="engage_prompt_input",
            )
            if prompt != prompt_value:
                on_prompt_change(prompt)

            # Action buttons
            btn_spacer, btn_reset, btn_submit = st.columns([2, 1, 1])
            with btn_reset:
                if st.button(
                    UIConfig.RESET_BUTTON,
                    use_container_width=True,
                    key="engage_reset_button",
                ):
                    on_reset()
            with btn_submit:
                if st.button(
                    UIConfig.SUBMIT_BUTTON,
                    use_container_width=True,
                    type="primary",
                    key="engage_submit_button",
                ):
                    on_submit()

            st.markdown("")

            # Password guess
            st.markdown(
                f'<p class="section-label">{UIConfig.PASSWORD_LABEL}</p>',
                unsafe_allow_html=True,
            )
            pwd_input_col, pwd_btn_col = st.columns([3, 1])
            with pwd_input_col:
                guess = st.text_input(
                    "Password guess",
                    value=password_guess,
                    placeholder=UIConfig.PASSWORD_PLACEHOLDER,
                    label_visibility="collapsed",
                    key="engage_password_input",
                )
                if guess != password_guess:
                    on_password_guess_change(guess)
            with pwd_btn_col:
                if st.button(
                    UIConfig.CHECK_PASSWORD_BUTTON,
                    use_container_width=True,
                    key="engage_check_password_button",
                ):
                    on_check_password()

        # ---- RIGHT COLUMN ----
        with right_col:
            # Header row: label + single toggle button
            label_col, btn_col = st.columns([3, 1])

            with label_col:
                st.markdown(
                    f'<p class="section-label">{UIConfig.MODEL_ANSWERS_LABEL}</p>',
                    unsafe_allow_html=True,
                )

            with btn_col:
                if responses:
                    user_label = ("Hide Prompt" if show_user_prompt
                                  else UIConfig.VIEW_PROMPT_BUTTON)
                    if st.button(
                        user_label,
                        use_container_width=True,
                        key="engage_toggle_view_prompt",
                    ):
                        on_toggle_user_prompt()

            if not responses:
                st.info(
                    "No responses yet. Enter a prompt and click Submit to generate responses."
                )
            else:
                for idx, response in enumerate(responses):
                    with st.container():
                        st.markdown(
                            f'<span class="response-badge">#{idx + 1}</span> '
                            f"**{response.model_name}**",
                            unsafe_allow_html=True,
                        )

                        if show_user_prompt and response.user_prompt:
                            st.markdown(
                                f'<div class="prompt-preview"><strong>User Prompt</strong><br/>{response.user_prompt}</div>',
                                unsafe_allow_html=True,
                            )

                        st.markdown(
                            f'<div class="answer-card">{response.response_text}</div>',
                            unsafe_allow_html=True,
                        )

                        if response.tokens_used:
                            st.markdown(
                                f'<p class="meta-caption">Tokens: {response.tokens_used} &middot; '
                                f'{response.timestamp.strftime("%Y-%m-%d %H:%M:%S")}</p>',
                                unsafe_allow_html=True,
                            )

                        st.markdown("---")


class StyleComponent:
    """Component for injecting custom styles."""

    @staticmethod
    def inject_styles() -> None:
        """Inject custom CSS styles into the application."""
        st.markdown(StyleConfig.CUSTOM_CSS, unsafe_allow_html=True)
