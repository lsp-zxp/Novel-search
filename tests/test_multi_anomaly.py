import asyncio
import json
from pathlib import Path

from novelops_agent.agent import build_agent
from novelops_agent.repository import JsonRepository
from novelops_agent.tools import build_tool_registry


def _write_dataset(path: Path, settlements: list[dict], *, share: float = 0.70) -> None:
    dataset = {
        "novels": [
            {
                "id": "N001",
                "title": "多异常作品",
                "platform": "demo_platform",
                "status": "settled",
                "submitted_at": "2026-07-01T00:00:00+08:00",
                "contract_id": "C001",
            }
        ],
        "workflow_events": [],
        "contracts": [
            {
                "id": "C001",
                "novel_id": "N001",
                "status": "active",
                "author_share": share,
                "settlement_cycle": "monthly",
                "effective_from": "2026-07-01",
                "effective_to": None,
                "source_clause": "合同第6.2条：作者分成比例。",
            }
        ],
        "settlements": settlements,
    }
    path.write_text(json.dumps(dataset, ensure_ascii=False), encoding="utf-8")


def _settlement(period: str, revenue: float, share: float, amount: float) -> dict:
    return {
        "id": f"S-{period}-{share}",
        "novel_id": "N001",
        "period": period,
        "distributable_revenue": revenue,
        "configured_author_share": share,
        "author_amount": amount,
        "status": "paid",
    }


def test_consistency_checks_every_period_not_just_latest(tmp_path):
    data_path = tmp_path / "data.json"
    _write_dataset(
        data_path,
        [
            _settlement("2026-08", 10000, 0.70, 7000),  # 一致
            _settlement("2026-09", 10000, 0.60, 6000),  # 少计 1000
        ],
    )
    tools = build_tool_registry(JsonRepository(data_path), enable_hybrid=False)

    result = tools["check_settlement_consistency"]("N001", "检查结算")

    assert result["detected"] is True
    assert result["affected_amount"] == 1000
    assert len(result["mismatches"]) == 1
    assert result["mismatches"][0]["period"] == "2026-09"


def test_report_lists_all_detected_anomalies(tmp_path):
    data_path = tmp_path / "data.json"
    _write_dataset(
        data_path,
        [
            # 同周期两条记录 → 重复结算，且分成 0.60 ≠ 合同 0.70 → 分成不一致
            _settlement("2026-09", 10000, 0.60, 6000),
            _settlement("2026-09", 10000, 0.60, 6000),
        ],
    )

    async def scenario():
        app = build_agent(
            repo=JsonRepository(data_path), model=False, enable_hybrid=False
        )
        result = await app.ainvoke(
            {"request": "检查结算异常", "novel_id": "N001"},
            config={"configurable": {"thread_id": "test-multi"}},
        )
        report = result["report"]
        types = {item["anomaly_type"] for item in report["anomalies"]}
        assert types == {"settlement_ratio_mismatch", "duplicate_settlement"}
        assert report["anomaly_type"] == "settlement_ratio_mismatch"  # primary
        assert len(report["anomalies"]) == 2

    asyncio.run(scenario())
