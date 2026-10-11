from __future__ import annotations

from linklens import app as app_module


def test_linklens_starts_without_fictional_case_data(monkeypatch):
    state = {}

    class FakeStreamlit:
        session_state = state

    monkeypatch.setattr(app_module, "st", FakeStreamlit)
    app_module._init()

    bundle = state["ll_bundle"]
    assert bundle.source_label == "No dataset loaded"
    assert bundle.graph.number_of_nodes() == 0
    assert state["ll_page"] == "Upload & Map Columns"
