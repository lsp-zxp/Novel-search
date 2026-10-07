from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from novelops_agent.supabase_rest import SupabaseRestClient

load_dotenv(ROOT / ".env")

TABLE_ORDER = [
    "authors", "novels", "workflow_events", "contracts",
    "settlements", "expected_anomalies",
]


def _secret_key() -> str | None:
    return os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")


def _normalize(table: str, row: dict) -> dict:
    output = row.copy()
    nullable_fields = {"novels": {"contract_id"}, "contracts": {"effective_to"}}
    for field in nullable_fields.get(table, set()):
        if output.get(field) == "":
            output[field] = None
    return output


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    url = os.getenv("SUPABASE_URL")
    key = _secret_key()
    if not url or not key:
        raise SystemExit("请先在 .env 配置 SUPABASE_URL 和 SUPABASE_SECRET_KEY。")

    dataset_path = ROOT / "seed_data" / "novelops_seed_50.json"
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    client = SupabaseRestClient(url, key)
    summary: dict[str, int] = {}
    for table in TABLE_ORDER:
        rows = [_normalize(table, row) for row in dataset[table]]
        for offset in range(0, len(rows), 100):
            client.upsert(table, rows[offset : offset + 100])
        actual = client.count(table)
        summary[table] = actual
        print(f"{table}: expected={len(rows)}, database={actual}")
        if actual < len(rows):
            raise RuntimeError(f"{table} 导入后的数量少于种子数据数量。")
    print(json.dumps({"status": "ok", "database_rows": summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
