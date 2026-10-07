from __future__ import annotations

import os
from typing import Any, TypedDict

from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from novelops_agent.repository import JsonRepository
from novelops_agent.llm import BailianJsonClient
from novelops_agent.intent import classify_intent_locally
from novelops_agent.prompts import (
    INTENT_SYSTEM_PROMPT,
    SCENE_CONFIG,
    planning_prompt,
    report_prompt,
)
from novelops_agent.schemas import (
    AnomalyFinding,
    IntentClassification,
    InvestigationPlan,
    InvestigationReport,
)
from novelops_agent.tools import Tool, build_tool_registry

load_dotenv()


class AgentState(TypedDict, total=False):
    request: str
    novel_id: str
    intent: dict[str, Any]
    goal: str
    plan: list[str]
    cursor: int
    traces: list[dict[str, Any]]
    report: dict[str, Any]
    approval: dict[str, Any]
    case: dict[str, Any]


_RISK_ORDER = {"low": 0, "medium": 1, "high": 2}


def _build_findings(detected_all: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate every detected rule hit into a multi-anomaly report summary.

    The single ``anomaly_type``/``risk_level`` fields keep the most-severe
    finding (tie-break: first in plan order) so routing, create_case, the web
    UI and the evaluator continue to work; ``anomalies`` carries the full list.
    """
    anomalies = [
        AnomalyFinding(
            anomaly_type=check["anomaly_type"],
            risk_level=check["risk_level"],
            affected_amount=float(check.get("affected_amount", 0)),
            conclusion=check["conclusion"],
            recommendation=check["recommendation"],
        )
        for check in detected_all
    ]
    if anomalies:
        primary = max(anomalies, key=lambda item: _RISK_ORDER[item.risk_level])
        anomaly_type = primary.anomaly_type
        risk_level = primary.risk_level
        affected_amount = round(sum(item.affected_amount for item in anomalies), 2)
        conclusion = "；".join(dict.fromkeys(item.conclusion for item in anomalies))
        recommendation = "；".join(
            dict.fromkeys(item.recommendation for item in anomalies)
        )
    else:
        anomaly_type = "none"
        risk_level = "low"
        affected_amount = 0.0
        conclusion = ""
        recommendation = ""
    return {
        "anomaly_type": anomaly_type,
        "risk_level": risk_level,
        "affected_amount": affected_amount,
        "conclusion": conclusion,
        "recommendation": recommendation,
        "anomalies": anomalies,
    }


def _get_model():
    api_key = os.getenv("LLM_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
    base_url = os.getenv("LLM_BASE_URL") or os.getenv("DASHSCOPE_BASE_URL")
    if not api_key or not base_url:
        return None
    return BailianJsonClient(
        model=os.getenv("LLM_MODEL", "deepseek-v4-pro"),
        api_key=api_key,
        base_url=base_url,
    )


def _get_repository():
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SECRET_KEY") or os.getenv(
        "SUPABASE_SERVICE_ROLE_KEY"
    )
    if supabase_url and supabase_key:
        from novelops_agent.supabase_repository import SupabaseRepository

        return SupabaseRepository(supabase_url, supabase_key)
    return JsonRepository()


def build_agent(
    repo: JsonRepository | None = None,
    model=None,
    *,
    enable_hybrid: bool = True,
):
    """Build the evidence-first investigation graph."""
    repository = repo or _get_repository()
    tools = build_tool_registry(repository, enable_hybrid=enable_hybrid)
    llm = model if model is not None else _get_model()

    async def classify_intent(state: AgentState) -> dict[str, Any]:
        fallback = classify_intent_locally(state["request"])
        if not llm:
            return {"intent": fallback.model_dump()}
        try:
            classified = await llm.parse(
                IntentClassification,
                system=INTENT_SYSTEM_PROMPT,
                user=f"用户请求：{state['request']}",
            )
            if classified.confidence < 0.7:
                classified = IntentClassification(
                    intent="full_audit",
                    confidence=classified.confidence,
                    normalized_request=classified.normalized_request,
                    reason=f"低置信度兜底：{classified.reason}",
                    source="llm",
                )
            return {"intent": classified.model_dump()}
        except RuntimeError:
            return {"intent": fallback.model_dump()}

    async def plan_investigation(state: AgentState) -> dict[str, Any]:
        intent_name = state["intent"]["intent"]
        required_tools = list(SCENE_CONFIG[intent_name]["tools"])
        if llm:
            try:
                plan = await llm.parse(
                    InvestigationPlan,
                    system=planning_prompt(intent_name),
                    user=(
                        f"小说ID：{state['novel_id']}\n"
                        f"标准化任务：{state['intent']['normalized_request']}"
                    ),
                )
            except RuntimeError:
                plan = InvestigationPlan(
                    novel_id=state["novel_id"],
                    goal=state["intent"]["normalized_request"],
                    tools=required_tools,
                )
        else:
            plan = InvestigationPlan(
                novel_id=state["novel_id"],
                goal=state["request"],
                tools=required_tools,
            )
        # The model may order tools, but code owns the scene boundary and completeness.
        ordered = [tool for tool in plan.tools if tool in required_tools]
        ordered.extend(tool for tool in required_tools if tool not in ordered)
        return {"goal": plan.goal, "plan": ordered, "cursor": 0, "traces": []}

    async def run_next_tool(state: AgentState) -> dict[str, Any]:
        name = state["plan"][state["cursor"]]
        tool: Tool = tools[name]
        try:
            tool_request = f"{state['request']}\n[scene:{state['intent']['intent']}]"
            result = tool(state["novel_id"], tool_request)
            trace = {"tool": name, "ok": True, "result": result}
        except (KeyError, ValueError) as exc:
            trace = {"tool": name, "ok": False, "result": {"error": str(exc)}}
        return {
            "traces": [*state.get("traces", []), trace],
            "cursor": state["cursor"] + 1,
        }

    def after_tool(state: AgentState) -> str:
        return "run_tool" if state["cursor"] < len(state["plan"]) else "synthesize"

    async def synthesize(state: AgentState) -> dict[str, Any]:
        intent_name = state["intent"]["intent"]
        successful = [trace for trace in state["traces"] if trace["ok"]]
        evidence = [
            trace["result"]["evidence"]
            for trace in successful
            if trace["result"].get("evidence")
        ]
        rule_checks = [
            trace["result"]
            for trace in successful
            if trace["tool"].startswith("check_")
        ]
        detected_all = [check for check in rule_checks if check.get("detected")]
        policy = next(
            (trace["result"] for trace in successful if trace["tool"] == "retrieve_policy"),
            {},
        )
        findings = _build_findings(detected_all)
        if detected_all and not policy.get("matches"):
            findings["recommendation"] += " 当前未检索到适用制度，请人工确认。"

        if llm:
            try:
                report = await llm.parse(
                    InvestigationReport,
                    system=report_prompt(intent_name),
                    user=(
                        f"任务：{state['intent']['normalized_request']}\n"
                        f"工具结果：{successful}"
                    ),
                )
            except RuntimeError:
                report = None
        else:
            report = None

        # Deterministic fields are always owned by the rule engine, never the LLM.
        deterministic = {
            "anomaly_type": findings["anomaly_type"],
            "risk_level": findings["risk_level"],
            "affected_amount": findings["affected_amount"],
            "evidence": evidence,
            "anomalies": findings["anomalies"],
        }
        if detected_all:
            deterministic["recommendation"] = findings["recommendation"]

        if report is not None:
            report = report.model_copy(update=deterministic)
        else:
            report = InvestigationReport(
                anomaly_type=findings["anomaly_type"],
                risk_level=findings["risk_level"],
                affected_amount=findings["affected_amount"],
                evidence=evidence,
                anomalies=findings["anomalies"],
                conclusion=findings["conclusion"] or "当前证据未发现该场景的业务异常。",
                recommendation=findings["recommendation"] or "保留本次调查记录。",
            )
        return {"report": report.model_dump()}

    def route_after_report(state: AgentState) -> str:
        return "human_review" if state["report"]["anomaly_type"] != "none" else END

    def human_review(state: AgentState) -> Command:
        decision = interrupt(
            {
                "action": "create_case",
                "message": "发现异常，是否批准创建处理工单？",
                "report": state["report"],
            }
        )
        if decision.get("approved"):
            return Command(update={"approval": decision}, goto="create_case")
        return Command(update={"approval": decision}, goto=END)

    def create_case(state: AgentState) -> dict[str, Any]:
        report = state["report"]
        return {
            "case": {
                "id": f"CASE-{state['novel_id']}-001",
                "novel_id": state["novel_id"],
                "status": "draft",
                "risk_level": report["risk_level"],
                "summary": report["conclusion"],
                "recommendation": report["recommendation"],
                "approved_by": state.get("approval", {}).get("reviewer", "demo_user"),
            }
        }

    graph = StateGraph(AgentState)
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("plan", plan_investigation)
    graph.add_node("run_tool", run_next_tool)
    graph.add_node("synthesize", synthesize)
    graph.add_node("human_review", human_review)
    graph.add_node("create_case", create_case)
    graph.add_edge(START, "classify_intent")
    graph.add_edge("classify_intent", "plan")
    graph.add_edge("plan", "run_tool")
    graph.add_conditional_edges("run_tool", after_tool, ["run_tool", "synthesize"])
    graph.add_conditional_edges("synthesize", route_after_report, ["human_review", END])
    graph.add_edge("create_case", END)
    return graph.compile(checkpointer=MemorySaver())
