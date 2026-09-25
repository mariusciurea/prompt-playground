from src.agent.tools import movie_reservation, read_from_disc, save_to_calendar
from src.engage import ENGAGE_LEVELS


def test_every_level_password_appears_in_its_system_prompt():
    for level in ENGAGE_LEVELS:
        assert level.password in level.system_prompt


def test_password_check_ignores_case_and_whitespace():
    level = ENGAGE_LEVELS[0]
    assert level.is_correct("  PromptInjection ")
    assert not level.is_correct("nope")
    assert not level.is_correct("")


def test_movie_reservation_lists_movies():
    result = movie_reservation("2026-10-01", "19:00")
    assert result["status"] == "success"
    assert len(result["available_movies"]) == 5


def test_save_to_calendar_returns_confirmation():
    event = save_to_calendar("Codebreaker", "2026-10-01", "19:00", "Room 5")["event"]
    assert event["title"] == "Movie: Codebreaker"
    assert event["confirmation_code"].startswith("RES-")


def test_read_from_disc_serves_decoy_for_env_files_and_dummy_data_otherwise():
    assert "GOOGLE_API_KEY" in read_from_disc(".env")["data"]
    assert "users" in read_from_disc("anything.txt")["data"]
    assert "users" in read_from_disc(None)["data"]
