import json
from pathlib import Path


DATA = Path(__file__).resolve().parents[1] / "seed_data" / "novelops_seed_50.json"


def load_data():
    return json.loads(DATA.read_text(encoding="utf-8"))


def test_contains_exactly_50_unique_novels():
    data = load_data()
    ids = [novel["id"] for novel in data["novels"]]
    titles = [novel["title"] for novel in data["novels"]]
    assert len(ids) == 50
    assert len(set(ids)) == 50
    assert len(set(titles)) == 50


def test_references_are_valid():
    data = load_data()
    novel_ids = {novel["id"] for novel in data["novels"]}
    author_ids = {author["id"] for author in data["authors"]}
    contract_ids = {contract["id"] for contract in data["contracts"]}
    assert all(novel["author_id"] in author_ids for novel in data["novels"])
    assert all(event["novel_id"] in novel_ids for event in data["workflow_events"])
    assert all(contract["novel_id"] in novel_ids for contract in data["contracts"])
    assert all(row["novel_id"] in novel_ids for row in data["settlements"])
    assert all(row["novel_id"] in novel_ids for row in data["expected_anomalies"])
    assert all(
        not novel["contract_id"] or novel["contract_id"] in contract_ids
        for novel in data["novels"]
    )


def test_dataset_contains_normal_and_multiple_anomaly_types():
    data = load_data()
    anomaly_types = {row["anomaly_type"] for row in data["expected_anomalies"]}
    assert {
        "settlement_ratio_mismatch",
        "missing_bill",
        "duplicate_settlement",
        "expired_contract_settlement",
        "editor_review_overdue",
    } <= anomaly_types
    anomalous_novels = {row["novel_id"] for row in data["expected_anomalies"]}
    assert any(novel["id"] not in anomalous_novels for novel in data["novels"])
