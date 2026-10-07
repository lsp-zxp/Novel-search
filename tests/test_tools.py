from pathlib import Path

from novelops_agent.repository import JsonRepository
from novelops_agent.tools import build_tool_registry


SEED_DATA = Path(__file__).parents[1] / "seed_data" / "novelops_seed_50.json"


def test_detects_share_mismatch_and_financial_impact():
    tools = build_tool_registry(JsonRepository())

    result = tools["check_settlement_consistency"]("N001", "检查结算")

    assert result["consistent"] is False
    assert result["contract_share"] == 0.70
    assert result["configured_share"] == 0.60
    assert result["affected_amount"] == 1000


def test_normal_settlement_is_consistent():
    tools = build_tool_registry(JsonRepository())

    result = tools["check_settlement_consistency"]("N002", "检查结算")

    assert result["consistent"] is True
    assert result["affected_amount"] == 0


def test_detects_missing_settlement():
    tools = build_tool_registry(JsonRepository(SEED_DATA), enable_hybrid=False)

    result = tools["check_missing_settlement"]("N002", "检查漏单")

    assert result["detected"] is True
    assert result["anomaly_type"] == "missing_bill"


def test_detects_duplicate_settlement():
    tools = build_tool_registry(JsonRepository(SEED_DATA), enable_hybrid=False)

    result = tools["check_duplicate_settlement"]("N003", "检查重复结算")

    assert result["detected"] is True
    assert result["anomaly_type"] == "duplicate_settlement"
    assert result["affected_amount"] > 0


def test_detects_expired_contract_settlement():
    tools = build_tool_registry(JsonRepository(SEED_DATA), enable_hybrid=False)

    result = tools["check_contract_validity"]("N004", "检查合同效期")

    assert result["detected"] is True
    assert result["anomaly_type"] == "expired_contract_settlement"


def test_detects_editor_review_overdue():
    tools = build_tool_registry(JsonRepository(SEED_DATA), enable_hybrid=False)

    result = tools["check_review_sla"]("N043", "检查审核超时")

    assert result["detected"] is True
    assert result["anomaly_type"] == "editor_review_overdue"
    assert result["business_days_elapsed"] > 3


def test_does_not_flag_ai_review_queue_as_editor_overdue():
    tools = build_tool_registry(JsonRepository(SEED_DATA), enable_hybrid=False)

    result = tools["check_review_sla"]("N047", "检查审核超时")

    assert result["detected"] is False
