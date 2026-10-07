from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class SupabaseRestClient:
    """Small dependency-free client for Supabase's PostgREST endpoint."""

    def __init__(self, url: str, secret_key: str, timeout: int = 30) -> None:
        self._base_url = url.rstrip("/") + "/rest/v1"
        self._key = secret_key
        self._timeout = timeout

    def _headers(self, *, prefer: str | None = None) -> dict[str, str]:
        headers = {
            "apikey": self._key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self._key.startswith("eyJ"):
            headers["Authorization"] = f"Bearer {self._key}"
        if prefer:
            headers["Prefer"] = prefer
        return headers

    def _request(
        self,
        method: str,
        table: str,
        *,
        params: list[tuple[str, str]] | None = None,
        body: Any | None = None,
        prefer: str | None = None,
    ) -> tuple[Any, dict[str, str]]:
        query = urlencode(params or [])
        endpoint = f"{self._base_url}/{table}" + (f"?{query}" if query else "")
        payload = None if body is None else json.dumps(body).encode("utf-8")
        request = Request(endpoint, data=payload, headers=self._headers(prefer=prefer), method=method)
        try:
            with urlopen(request, timeout=self._timeout) as response:
                raw = response.read()
                data = json.loads(raw.decode("utf-8")) if raw else None
                return data, dict(response.headers.items())
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Supabase REST 请求失败：HTTP {exc.code}，table={table}，{detail}"
            ) from exc

    def upsert(self, table: str, rows: list[dict[str, Any]]) -> None:
        self._request(
            "POST", table, params=[("on_conflict", "id")], body=rows,
            prefer="resolution=merge-duplicates,return=minimal",
        )

    def select(
        self,
        table: str,
        *,
        filters: dict[str, str] | None = None,
        order: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        params: list[tuple[str, str]] = [("select", "*")]
        params.extend((name, f"eq.{value}") for name, value in (filters or {}).items())
        if order:
            params.append(("order", order))
        if limit is not None:
            params.append(("limit", str(limit)))
        data, _ = self._request("GET", table, params=params)
        return data or []

    def count(self, table: str) -> int:
        data, headers = self._request(
            "GET", table, params=[("select", "id"), ("limit", "1")], prefer="count=exact",
        )
        content_range = next(
            (value for key, value in headers.items() if key.lower() == "content-range"), None,
        )
        if content_range and "/" in content_range:
            total = content_range.rsplit("/", 1)[1]
            if total.isdigit():
                return int(total)
        return len(data or [])
