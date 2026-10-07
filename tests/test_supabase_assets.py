import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_supabase_migration_contains_all_business_tables_and_rls():
    sql = (ROOT / "database" / "migrations" / "001_initial_schema.sql").read_text(
        encoding="utf-8"
    )
    for table in (
        "authors",
        "novels",
        "workflow_events",
        "contracts",
        "settlements",
        "expected_anomalies",
    ):
        assert f"create table if not exists public.{table}" in sql
        assert f"alter table public.{table} enable row level security" in sql
        assert f"revoke all on table public.{table} from anon, authenticated" in sql


def test_seed_novels_have_platform_for_rag_filtering():
    data = json.loads(
        (ROOT / "seed_data" / "novelops_seed_50.json").read_text(encoding="utf-8")
    )
    assert len(data["novels"]) == 50
    assert all(novel.get("platform") == "番茄小说" for novel in data["novels"])
