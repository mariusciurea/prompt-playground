"""Build the Reservation agent."""

from google.adk.agents import Agent
from google.adk.models import Gemini

from app.agents.reservation.prompt import RESERVATION_AGENT_INSTRUCTION
from app.agents.reservation.tools import movie_reservation, read_from_disc, save_to_calendar

APP_NAME = "reservation"


def build_reservation_agent(model: Gemini) -> Agent:
    """Create the cinema assistant, including its deliberately over-broad `read_from_disc`."""
    return Agent(
        name="reservation_agent",
        model=model,
        description="A cinema reservation assistant that can book movies and read stored data.",
        instruction=RESERVATION_AGENT_INSTRUCTION,
        tools=[movie_reservation, save_to_calendar, read_from_disc],
    )
