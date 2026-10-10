"""Optional Streamlit AppTest smoke checks for each navigation page."""
import pytest

pytest.importorskip("streamlit.testing.v1")
from streamlit.testing.v1 import AppTest
from pathlib import Path

APP = Path(__file__).parents[1] / "src" / "app.py"
PAGES = [
    "Overview",
    "Upload & Map Columns",
    "Network Explorer",
    "Key Players",
    "Groups & Communities",
    "Timeline",
    "Suspicious Patterns",
    "Case Report",
    "Glossary",
]


@pytest.mark.parametrize("page", PAGES)
def test_each_page_renders_without_exception(page):
    app = AppTest.from_file(str(APP), default_timeout=45).run()
    assert not app.exception
    app.radio[0].set_value(page).run()
    assert not app.exception
