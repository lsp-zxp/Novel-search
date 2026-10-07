from __future__ import annotations

import os
from typing import Any

from novelops_agent.supabase_rest import SupabaseRestClient


class SupabaseRepository:
    """Supabase-backed business repository for the Agent."""

    def __init__(self, url: str | None = None, secret_key: str | None = None) -> None:
        endpoint = url or os.getenv("SUPABASE_URL")
        key = secret_key or os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not endpoint or not key:
            raise RuntimeError("Supabase 配置不完整。")
        self._client = SupabaseRestClient(endpoint, key)

    def novel(self, novel_id: str) -> dict[str, Any]:
        rows = self._client.select("novels", filters={"id": novel_id}, limit=1)
        if not rows:
            raise KeyError(f"novels 中不存在 ID={novel_id}")
        row = rows[0]
        return {**row, "status": row["current_status"], "author": row["author_pen_name"]}

    def novels(self) -> list[dict[str, Any]]:
        return self._client.select("novels", order="id.asc")

    def workflow(self, novel_id: str) -> list[dict[str, Any]]:
        rows = self._client.select(
            "workflow_events", filters={"novel_id": novel_id}, order="occurred_at.asc",
        )
        return [{**row, "at": row["occurred_at"]} for row in rows]

    def contract(self, novel_id: str) -> dict[str, Any]:
        rows = self._client.select(
            "contracts", filters={"novel_id": novel_id}, order="effective_from.desc", limit=1,
        )
        if not rows:
            raise KeyError(f"contracts 中不存在 novel_id={novel_id}")
        return rows[0]

    def settlement(self, novel_id: str) -> dict[str, Any]:
        rows = self._client.select(
            "settlements", filters={"novel_id": novel_id}, order="created_at.desc", limit=1,
        )
        if not rows:
            raise KeyError(f"settlements 中不存在 novel_id={novel_id}")
        return rows[0]

    def settlements(self, novel_id: str) -> list[dict[str, Any]]:
        return self._client.select(
            "settlements",
            filters={"novel_id": novel_id},
            order="created_at.asc",
        )
