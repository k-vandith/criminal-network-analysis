from src.services.case_store import CaseStore


def test_case_roundtrip(tmp_path):
    store = CaseStore(tmp_path / "cases.json")
    saved = store.save_case({"name": "OPERATION NIGHTFALL", "entities": ["P1"], "notes": "review"})
    assert saved["id"].startswith("CASE-")
    again = store.get(saved["id"])
    assert again["name"] == "OPERATION NIGHTFALL"
    assert again["entities"] == ["P1"]
    updated = store.save_case({"id": saved["id"], "name": "OPERATION NIGHTFALL", "entities": ["P1", "P2"]})
    assert len(store.list_cases()) == 1
    assert updated["entities"] == ["P1", "P2"]
