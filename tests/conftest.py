import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from streamlit.testing.v1.element_tree import ButtonGroup  # noqa: E402

from src.config import Settings, get_settings  # noqa: E402


@pytest.fixture(autouse=True)
def _isolated_settings(monkeypatch):
    """Never read the developer's real .env or environment in tests."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setitem(Settings.model_config, "env_file", None)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _apptest_single_select_button_groups(monkeypatch):
    """AppTest only models multi-select button groups (st.feedback); teach it
    the single-select ones used by st.pills / st.segmented_control."""

    def indices(self):
        value = self.value
        if value is None:
            return []
        values = value if isinstance(value, list) else [value]
        return [self.options.index(self.format_func(v)) for v in values]

    monkeypatch.setattr(ButtonGroup, "indices", property(indices))
