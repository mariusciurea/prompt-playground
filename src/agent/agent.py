"""Google ADK agent definition for the Event Reservation assistant."""

import os
import asyncio
import concurrent.futures
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from google.genai import types

from src.agent.prompt import RESERVATION_AGENT_INSTRUCTION
from src.agent.tools import movie_reservation, save_to_calendar, read_from_disc

load_dotenv()

AGENT_MODEL = os.getenv("GEMINI_MODEL_ID", "gemini-2.0-flash")

root_agent = Agent(
    name="reservation_agent",
    model=AGENT_MODEL,
    description="A cinema reservation assistant that can book movies and read stored data.",
    instruction=RESERVATION_AGENT_INSTRUCTION,
    tools=[movie_reservation, save_to_calendar, read_from_disc],
)


def _run_coroutine(coro):
    """Run an async coroutine safely, even inside Streamlit's event loop."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


class ReservationAgentService:
    """Wraps the ADK agent for use inside Streamlit."""

    def __init__(self):
        self._runner = InMemoryRunner(root_agent, app_name="reservation_app")
        self._user_id = "streamlit_user"
        self._session_id: str | None = None

    def _ensure_session(self) -> str:
        if self._session_id is None:
            session = _run_coroutine(
                self._runner.session_service.create_session(
                    app_name="reservation_app", user_id=self._user_id
                )
            )
            self._session_id = session.id
        return self._session_id

    def send_message(self, text: str) -> str:
        """Send a user message and return the agent's text response."""
        session_id = self._ensure_session()
        user_message = types.Content(
            role="user", parts=[types.Part(text=text)]
        )

        final_text_parts: list[str] = []
        for event in self._runner.run(
            user_id=self._user_id,
            session_id=session_id,
            new_message=user_message,
        ):
            if event.content and event.content.parts and not event.partial:
                for part in event.content.parts:
                    if part.text:
                        final_text_parts.append(part.text)

        return "\n".join(final_text_parts) if final_text_parts else "No response."

    def reset_session(self):
        """Start a fresh conversation."""
        self._session_id = None
