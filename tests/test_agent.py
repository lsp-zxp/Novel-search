import asyncio
from pathlib import Path

from langgraph.types import Command

from novelops_agent.agent import build_agent
from novelops_agent.repository import JsonRepository


SAMPLE_DATA = Path(__file__).parents[1] / "novelops_agent" / "data" / "sample_data.json"


def test_agent_pauses_for_approval_then_creates_case():
    async def scenario():
        app = build_agent(
            repo=JsonRepository(SAMPLE_DATA), model=False, enable_hybrid=False
        )
        config = {"configurable": {"thread_id": "test-approval"}}
        paused = await app.ainvoke(
            {"request": "检查结算异常", "novel_id": "N001"}, config=config
        )
        assert paused["report"]["anomaly_type"] == "settlement_ratio_mismatch"
        assert "__interrupt__" in paused

        final = await app.ainvoke(
            Command(resume={"approved": True, "reviewer": "tester"}),
            config=config,
        )
        assert final["case"]["status"] == "draft"
        assert final["case"]["approved_by"] == "tester"

    asyncio.run(scenario())


def test_agent_finishes_without_approval_when_no_anomaly():
    async def scenario():
        app = build_agent(
            repo=JsonRepository(SAMPLE_DATA), model=False, enable_hybrid=False
        )
        config = {"configurable": {"thread_id": "test-normal"}}
        result = await app.ainvoke(
            {"request": "检查结算异常", "novel_id": "N002"}, config=config
        )
        assert result["report"]["anomaly_type"] == "none"
        assert "__interrupt__" not in result

    asyncio.run(scenario())
