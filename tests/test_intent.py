import asyncio
from pathlib import Path

from novelops_agent.agent import build_agent
from novelops_agent.intent import classify_intent_locally
from novelops_agent.prompts import SCENE_CONFIG
from novelops_agent.repository import JsonRepository


SEED_DATA = Path(__file__).parents[1] / "seed_data" / "novelops_seed_50.json"


def test_local_intent_boundaries():
    cases = {
        "这个月为什么没有生成稿费账单": "settlement_audit",
        "这本书的合同是否已经到期": "contract_audit",
        "AI审核通过后编辑复审超时了": "review_sla",
        "番茄第三个月全勤门槛是多少": "policy_lookup",
        "番茄签约第三个月需要多少听读收益才能获得全勤": "policy_lookup",
        "全面检查这本书从审核到结算有没有问题": "full_audit",
        "合同到期后为什么还有结算": "full_audit",
    }
    for request, expected in cases.items():
        assert classify_intent_locally(request).intent == expected


def test_every_scene_has_a_dedicated_prompt_and_tool_set():
    assert set(SCENE_CONFIG) == {
        "settlement_audit",
        "contract_audit",
        "review_sla",
        "policy_lookup",
        "full_audit",
    }
    assert all(scene["planning"] and scene["reporting"] for scene in SCENE_CONFIG.values())
    assert all(scene["tools"] for scene in SCENE_CONFIG.values())


def test_review_intent_routes_only_to_review_scene_tools():
    async def scenario():
        app = build_agent(
            repo=JsonRepository(SEED_DATA), model=False, enable_hybrid=False
        )
        result = await app.ainvoke(
            {"request": "检查编辑复审是否超时", "novel_id": "N043"},
            config={"configurable": {"thread_id": "intent-review"}},
        )
        assert result["intent"]["intent"] == "review_sla"
        assert result["plan"] == SCENE_CONFIG["review_sla"]["tools"]
        assert result["report"]["anomaly_type"] == "editor_review_overdue"

    asyncio.run(scenario())
