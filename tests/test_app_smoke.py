"""Drive each view with Streamlit's AppTest, using fake backends (no network)."""

import pytest
from streamlit.testing.v1 import AppTest

from src.agent.agent import AgentError, AgentReply, ToolCall
from src.models import ModelResponse

TIMEOUT = 30


class FakeAIService:
    model_name = "Fake"

    def __init__(self):
        self.prompts = []

    def generate_response(self, prompt_data, on_chunk=None):
        self.prompts.append(prompt_data)
        if on_chunk:
            on_chunk("fake ")
            on_chunk("answer")
        return ModelResponse(
            model_name="Fake",
            response_text="fake answer",
            user_prompt=prompt_data.user_prompt,
            system_prompt=prompt_data.system_prompt,
            tokens_used=7,
            latency_seconds=0.1,
            temperature=prompt_data.temperature,
        )


class FakeAgent:
    def __init__(self, error=None):
        self.error, self.resets = error, 0

    def send_message(self, text):
        if self.error:
            raise self.error
        return AgentReply(
            "Here are the movies", [ToolCall("movie_reservation", {"date": "d"}, {"ok": 1})]
        )

    def reset_session(self):
        self.resets += 1


@pytest.fixture
def ai_service(monkeypatch):
    service = FakeAIService()
    monkeypatch.setattr("src.state._cached_ai_service", lambda: service)
    return service


def view(name: str) -> AppTest:
    return AppTest.from_string(
        f"from src.views import {name}\n{name}.render()", default_timeout=TIMEOUT
    )


def texts(elements) -> list[str]:
    return [element.value for element in elements]


@pytest.mark.parametrize("name", ["playground", "engage", "reservation", "documentation"])
def test_views_show_setup_error_without_api_key(name):
    app = view(name).run()
    assert not app.exception
    if name != "documentation":
        assert any("GEMINI_API_KEY" in text for text in texts(app.error))


def test_main_app_renders_with_navigation():
    app = AppTest.from_file("app.py", default_timeout=TIMEOUT).run()
    assert not app.exception


def click(app: AppTest, label: str) -> AppTest:
    next(button for button in app.button if button.label == label).click()
    return app.run()


def test_playground_runs_prompt_and_shows_response(ai_service):
    app = view("playground").run()
    app.text_area(key="playground_user_prompt").set_value("Hello?")
    app.text_area(key="playground_system_prompt").set_value("Be nice")
    click(app, "Run")

    assert not app.exception
    assert ai_service.prompts[-1].user_prompt == "Hello?"
    assert ai_service.prompts[-1].system_prompt == "Be nice"
    assert any("fake answer" in text for text in texts(app.markdown))


def test_playground_rejects_empty_prompt(ai_service):
    app = click(view("playground").run(), "Run")
    assert not ai_service.prompts
    assert any("user prompt" in text.lower() for text in texts(app.warning))


def test_load_example_fills_both_prompts(monkeypatch):
    from src.views import playground

    fake_state = {playground.EXAMPLE_KEY: "🌍 Translator"}
    monkeypatch.setattr(playground.st, "session_state", fake_state)
    playground._load_example()
    system, user = playground.EXAMPLES["🌍 Translator"]
    assert fake_state[playground.SYSTEM_KEY] == system
    assert fake_state[playground.USER_KEY] == user


def test_engage_password_flow(ai_service):
    app = view("engage").run()
    app.text_input(key="engage_guess").set_value("wrong")
    click(app, "Check password")
    assert any("Wrong password" in text for text in texts(app.error))

    app.text_input(key="engage_guess").set_value("PromptInjection")
    click(app, "Check password")
    assert any("Congratulations" in text for text in texts(app.success))
    assert any(b.label == "Next level" for b in app.button)


def test_reservation_chat_shows_reply_and_tool_calls(monkeypatch):
    agent = FakeAgent()
    monkeypatch.setattr("src.state.get_reservation_agent", lambda: (agent, None))
    monkeypatch.setattr("src.views.reservation.get_reservation_agent", lambda: (agent, None))

    app = view("reservation").run()
    app.chat_input[0].set_value("movies please").run()

    assert not app.exception
    roles = [message.name for message in app.chat_message]
    assert roles == ["user", "assistant"]
    assert any("Here are the movies" in text for text in texts(app.markdown))
    assert any("movie_reservation" in text for text in texts(app.markdown))


def test_reservation_agent_error_is_shown_not_stored(monkeypatch):
    agent = FakeAgent(error=AgentError("boom"))
    monkeypatch.setattr("src.views.reservation.get_reservation_agent", lambda: (agent, None))

    app = view("reservation").run()
    app.chat_input[0].set_value("hi").run()

    assert any("boom" in text for text in texts(app.error))
    assert not app.session_state["_reservation_state"].messages
