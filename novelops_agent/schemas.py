from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class IntentClassification(BaseModel):
    intent: Literal[
        "settlement_audit",
        "contract_audit",
        "review_sla",
        "policy_lookup",
        "full_audit",
    ]
    confidence: float = Field(ge=0, le=1)
    normalized_request: str
    reason: str
    source: Literal["llm", "rule_fallback"] = "llm"


class InvestigationPlan(BaseModel):
    """LLM-generated tool execution plan."""

    novel_id: str = Field(description="待调查的小说ID")
    goal: str = Field(description="调查目标")
    tools: list[
        Literal[
            "get_novel_context",
            "get_contract_terms",
            "get_settlement_summary",
            "retrieve_policy",
            "check_settlement_consistency",
            "check_missing_settlement",
            "check_duplicate_settlement",
            "check_contract_validity",
            "check_review_sla",
        ]
    ] = Field(min_length=1, description="按执行顺序排列的工具名")


class AnomalyFinding(BaseModel):
    """A single deterministic rule hit, kept verbatim from a check_* tool."""

    anomaly_type: str
    risk_level: Literal["low", "medium", "high"]
    affected_amount: float = 0
    conclusion: str
    recommendation: str


class InvestigationReport(BaseModel):
    anomaly_type: str
    risk_level: Literal["low", "medium", "high"]
    conclusion: str
    evidence: list[str]
    affected_amount: float = 0
    recommendation: str
    # Full list of detected anomalies; empty when the investigation is clean.
    # The single fields above are derived aggregates (most-severe type, summed amount).
    anomalies: list[AnomalyFinding] = []


class ToolTrace(BaseModel):
    tool: str
    ok: bool
    result: dict[str, Any]
