"""Local JSON persistence for investigation cases. Offline only."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


class CaseStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")

    def list_cases(self) -> list[dict[str, Any]]:
        data = json.loads(self.path.read_text(encoding="utf-8") or "[]")
        return data if isinstance(data, list) else []

    def save_case(self, case: dict[str, Any]) -> dict[str, Any]:
        cases = self.list_cases()
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        if not case.get("id"):
            case["id"] = f"CASE-{uuid4().hex[:8].upper()}"
            case["created"] = now
        case["updated"] = now
        case.setdefault("name", "Untitled case")
        case.setdefault("description", "")
        case.setdefault("entities", [])
        case.setdefault("relationships", [])
        case.setdefault("signals", [])
        case.setdefault("notes", "")
        case.setdefault("findings", [])
        replaced = False
        for i, existing in enumerate(cases):
            if existing.get("id") == case["id"]:
                cases[i] = case
                replaced = True
                break
        if not replaced:
            cases.append(case)
        self.path.write_text(json.dumps(cases, indent=2), encoding="utf-8")
        return case

    def get(self, case_id: str) -> dict[str, Any] | None:
        for case in self.list_cases():
            if case.get("id") == case_id:
                return case
        return None
