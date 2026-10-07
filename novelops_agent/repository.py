from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class JsonRepository:
    """Read-only demo repository. Replace this class with real service clients later."""

    def __init__(self, data_path: Path | None = None) -> None:
        path = data_path or Path(__file__).parent / "data" / "sample_data.json"
        self._data: dict[str, list[dict[str, Any]]] = json.loads(
            path.read_text(encoding="utf-8")
        )

    def novel(self, novel_id: str) -> dict[str, Any]:
        row = self._find_one("novels", novel_id)
        if "current_status" in row:
            row.setdefault("status", row["current_status"])
        if "author_pen_name" in row:
            row.setdefault("author", row["author_pen_name"])
        return row

    def novels(self) -> list[dict[str, Any]]:
        return [row.copy() for row in self._data["novels"]]

    def workflow(self, novel_id: str) -> list[dict[str, Any]]:
        return [row for row in self._data["workflow_events"] if row["novel_id"] == novel_id]

    def contract(self, novel_id: str) -> dict[str, Any]:
        return self._find_by_novel("contracts", novel_id)

    def settlement(self, novel_id: str) -> dict[str, Any]:
        return self._find_by_novel("settlements", novel_id)

    def settlements(self, novel_id: str) -> list[dict[str, Any]]:
        return [
            row.copy()
            for row in self._data["settlements"]
            if row["novel_id"] == novel_id
        ]

    def _find_one(self, table: str, row_id: str) -> dict[str, Any]:
        for row in self._data[table]:
            if row["id"] == row_id:
                return row.copy()
        raise KeyError(f"{table} 中不存在 ID={row_id}")

    def _find_by_novel(self, table: str, novel_id: str) -> dict[str, Any]:
        for row in self._data[table]:
            if row["novel_id"] == novel_id:
                return row.copy()
        raise KeyError(f"{table} 中不存在 novel_id={novel_id}")
