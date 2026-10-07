from novelops_agent.rag import KnowledgeBase
from novelops_agent.repository import JsonRepository
from novelops_agent.tools import build_tool_registry


def test_retrieves_current_settlement_policy_with_citation():
    knowledge = KnowledgeBase()
    results = knowledge.search(
        "合同分成比例和结算系统配置不一致如何处理",
        business_type="settlement",
        platform="demo_platform",
        effective_at="2026-09-30",
        top_k=3,
    )
    assert results
    assert any("第3.1条 分成比例" in result["citation"] for result in results)
    assert all(result["version"] != "2025-v1" for result in results)


def test_filters_policy_by_effective_date():
    knowledge = KnowledgeBase()
    results = knowledge.search(
        "最低结算门槛",
        business_type="settlement",
        platform="demo_platform",
        effective_at="2025-09-30",
        top_k=5,
    )
    assert results
    assert any(result["version"] == "2025-v1" for result in results)
    assert all(result["version"] != "2026-v2" for result in results)


def test_rag_tool_returns_policy_evidence():
    tools = build_tool_registry(JsonRepository(), KnowledgeBase(), enable_hybrid=False)
    result = tools["retrieve_policy"]("N001", "调查合同分成与结算金额异常")
    assert result["matches"]
    assert result["evidence"].startswith("规则依据：")
    assert "作者结算管理办法" in result["evidence"]


def test_policy_lookup_without_novel_context():
    tools = build_tool_registry(JsonRepository(), KnowledgeBase(), enable_hybrid=False)
    result = tools["retrieve_policy"]("", "番茄第三个月全勤门槛是多少")
    assert result["matches"]
    assert result["platform"] == "番茄小说"


def test_retrieves_fanqie_rules_without_mixing_demo_platform():
    knowledge = KnowledgeBase()
    results = knowledge.search(
        "全勤听读收益1500元",
        business_type="settlement",
        platform="番茄小说",
        effective_at="2026-10-07",
        top_k=5,
    )
    assert results
    assert any(result["document_id"] == "fanqie-attendance-2026-10" for result in results)
    assert all(result["platform"] in {"番茄小说", "cross_platform"} for result in results)
    assert all(result["verification_status"] == "pending_official_source" for result in results)


def test_unknown_effective_date_document_is_searchable_with_warning_metadata():
    knowledge = KnowledgeBase()
    results = knowledge.search(
        "签作者本人 合约期5年",
        business_type="contract",
        platform="晋江文学城",
        effective_at="2026-10-07",
        top_k=3,
    )
    assert results
    assert results[0]["effective_from"] is None
    assert results[0]["verification_status"] == "pending_official_source"
