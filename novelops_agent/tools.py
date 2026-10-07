from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime
import os
from typing import Any

from novelops_agent.embeddings import OpenAIEmbeddingProvider
from novelops_agent.hybrid_retriever import HybridRetriever
from novelops_agent.rag import KnowledgeBase
from novelops_agent.reranker import OpenAIReranker
from novelops_agent.repository import JsonRepository
from novelops_agent.vector_index import JsonVectorIndex

Tool = Callable[[str, str], dict[str, Any]]


def build_tool_registry(
    repo: JsonRepository,
    knowledge_base: KnowledgeBase | None = None,
    hybrid_retriever: HybridRetriever | None = None,
    *,
    enable_hybrid: bool = True,
) -> dict[str, Tool]:
    knowledge = knowledge_base or KnowledgeBase()
    hybrid = hybrid_retriever
    if hybrid is None and enable_hybrid:
        hybrid = _build_default_hybrid_retriever(knowledge)

    def get_novel_context(novel_id: str, request: str = "") -> dict[str, Any]:
        novel = repo.novel(novel_id)
        return {
            "novel": novel,
            "workflow": repo.workflow(novel_id),
            "evidence": f"作品《{novel['title']}》当前状态为 {novel['status']}",
        }

    def get_contract_terms(novel_id: str, request: str = "") -> dict[str, Any]:
        contract = repo.contract(novel_id)
        return {
            "contract_id": contract["id"],
            "status": contract["status"],
            "author_share": contract["author_share"],
            "settlement_cycle": contract["settlement_cycle"],
            "source_clause": contract["source_clause"],
            "evidence": contract["source_clause"],
        }

    def get_settlement_summary(novel_id: str, request: str = "") -> dict[str, Any]:
        settlement = repo.settlement(novel_id)
        return {
            **settlement,
            "evidence": (
                f"{settlement['period']}结算记录：可分配收入"
                f"{settlement['distributable_revenue']:.2f}元，系统分成比例"
                f"{settlement['configured_author_share']:.0%}，作者金额"
                f"{settlement['author_amount']:.2f}元"
            ),
        }

    def retrieve_policy(novel_id: str, request: str = "") -> dict[str, Any]:
        novel = repo.novel(novel_id) if novel_id else {}
        if novel:
            platform = novel.get("platform")
        elif "晋江" in request:
            platform = "晋江文学城"
        elif "番茄" in request:
            platform = "番茄小说"
        else:
            platform = None
        lowered = request.lower()
        if "[scene:review_sla]" in lowered or any(
            word in request for word in ("审核", "复审", "超时", "低质")
        ):
            business_type = "review"
            query_suffix = "AI预审 编辑复审 审核时效 超时处理"
        elif "[scene:contract_audit]" in lowered:
            business_type = "contract"
            query_suffix = "合同状态 生效日期 失效日期 签约规则"
        elif "[scene:settlement_audit]" in lowered or any(
            word in request for word in ("结算", "稿费", "金额", "分成", "账单", "漏单")
        ):
            business_type = "settlement"
            query_suffix = "合同分成比例 结算配置 金额异常 处理规则"
        elif any(
            word in request for word in ("合同", "签约", "生效", "失效", "到期")
        ):
            business_type = "contract"
            query_suffix = "合同状态 生效日期 失效日期 签约规则"
        else:
            business_type = "settlement"
            query_suffix = "合同分成比例 结算配置 金额异常 处理规则"
        try:
            settlement = repo.settlement(novel_id)
            effective_at = f"{settlement['period']}-01"
        except KeyError:
            effective_at = date.today().isoformat()
        query = f"{request} {query_suffix}"
        if hybrid:
            matches = hybrid.search(
                query,
                business_type=business_type,
                platform=platform,
                effective_at=effective_at,
                final_k=3,
            )
            retrieval_mode = "hybrid_bm25_vector_rrf_rerank" if hybrid.reranker else "hybrid_bm25_vector_rrf"
        else:
            matches = knowledge.search(
                query,
                business_type=business_type,
                platform=platform,
                effective_at=effective_at,
                top_k=3,
            )
            retrieval_mode = "bm25_fallback"
        citations = [f"{match['citation']}：{match['text']}" for match in matches]
        return {
            "query": query,
            "effective_at": effective_at,
            "platform": platform,
            "business_type": business_type,
            "retrieval_mode": retrieval_mode,
            "matches": matches,
            "evidence": "规则依据：" + "；".join(citations) if citations else "未检索到适用规则",
        }

    def check_settlement_consistency(novel_id: str, request: str = "") -> dict[str, Any]:
        contract = repo.contract(novel_id)
        rows = repo.settlements(novel_id)
        mismatches: list[dict[str, Any]] = []
        for row in rows:
            expected = round(row["distributable_revenue"] * contract["author_share"], 2)
            actual = round(row["author_amount"], 2)
            impact = round(expected - actual, 2)
            if contract["author_share"] != row["configured_author_share"] or impact != 0:
                mismatches.append(
                    {
                        "period": row["period"],
                        "contract_share": contract["author_share"],
                        "configured_share": row["configured_author_share"],
                        "expected_author_amount": expected,
                        "actual_author_amount": actual,
                        "impact": impact,
                    }
                )
        detected = bool(mismatches)
        affected = round(sum(item["impact"] for item in mismatches), 2)
        # Single-value fields reflect the first mismatch for backward compatibility.
        first = mismatches[0] if mismatches else None
        evidence_parts = [
            f"{item['period']}合同分成比例{item['contract_share']:.0%}，系统结算比例"
            f"{item['configured_share']:.0%}；预计作者金额"
            f"{item['expected_author_amount']:.2f}元，实际{item['actual_author_amount']:.2f}元"
            for item in mismatches
        ]
        return {
            "detected": detected,
            "anomaly_type": "settlement_ratio_mismatch" if detected else "none",
            "risk_level": "high" if detected else "low",
            "consistent": not detected,
            "contract_share": contract["author_share"],
            "configured_share": first["configured_share"] if first else None,
            "expected_author_amount": first["expected_author_amount"] if first else None,
            "actual_author_amount": first["actual_author_amount"] if first else None,
            "affected_amount": affected,
            "mismatches": mismatches,
            "conclusion": (
                "合同分成比例与结算系统配置不一致，导致作者金额错计。"
                if detected
                else "结算比例与金额一致。"
            ),
            "recommendation": "暂停本期付款，核对生效合同版本并重新计算结算金额。",
            "evidence": (
                "；".join(evidence_parts)
                if detected
                else "合同分成比例与系统结算配置一致，金额核对无误。"
            ),
        }

    def check_missing_settlement(novel_id: str, request: str = "") -> dict[str, Any]:
        novel = repo.novel(novel_id)
        rows = repo.settlements(novel_id)
        expected = novel.get("status") in {"settlement_pending", "settled"}
        detected = expected and not rows
        return {
            "detected": detected,
            "anomaly_type": "missing_bill" if detected else "none",
            "risk_level": "high" if detected else "low",
            "affected_amount": 0,
            "conclusion": (
                "作品已进入结算阶段，但未找到应生成的结算记录。"
                if detected
                else "未发现结算漏单。"
            ),
            "recommendation": "暂停后续出款，核对出账批次并补生成结算记录。",
            "evidence": (
                f"作品状态为{novel.get('status')}，结算记录数为{len(rows)}"
            ),
        }

    def check_duplicate_settlement(novel_id: str, request: str = "") -> dict[str, Any]:
        rows = repo.settlements(novel_id)
        by_period: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            by_period.setdefault(row["period"], []).append(row)
        duplicates = {period: items for period, items in by_period.items() if len(items) > 1}
        detected = bool(duplicates)
        affected = round(
            sum(
                float(item.get("author_amount", 0))
                for items in duplicates.values()
                for item in items[1:]
            ),
            2,
        )
        detail = ", ".join(f"{period}:{len(items)}条" for period, items in duplicates.items())
        return {
            "detected": detected,
            "anomaly_type": "duplicate_settlement" if detected else "none",
            "risk_level": "high" if detected else "low",
            "affected_amount": affected,
            "conclusion": (
                "同一作品的同一结算周期存在多条结算记录。"
                if detected
                else "未发现重复结算。"
            ),
            "recommendation": "冻结重复记录，核对幂等键和已支付状态后再处理。",
            "evidence": f"各结算周期记录数：{detail or '无重复'}",
        }

    def check_contract_validity(novel_id: str, request: str = "") -> dict[str, Any]:
        contract = repo.contract(novel_id)
        rows = repo.settlements(novel_id)
        effective_to = contract.get("effective_to")
        invalid_rows: list[dict[str, Any]] = []
        if contract.get("status") == "expired" or effective_to:
            for row in rows:
                period_start = date.fromisoformat(f"{row['period']}-01")
                expired_before_period = bool(
                    effective_to and date.fromisoformat(effective_to) < period_start
                )
                if contract.get("status") == "expired" and (
                    not effective_to or expired_before_period
                ):
                    invalid_rows.append(row)
        detected = bool(invalid_rows)
        affected = round(sum(float(row["author_amount"]) for row in invalid_rows), 2)
        return {
            "detected": detected,
            "anomaly_type": "expired_contract_settlement" if detected else "none",
            "risk_level": "high" if detected else "low",
            "affected_amount": affected,
            "conclusion": (
                "结算周期晚于合同失效日期，仍然生成了结算记录。"
                if detected
                else "未发现失效合同结算。"
            ),
            "recommendation": "暂停付款，核对合同效期及结算期间后撤销或重算。",
            "evidence": (
                f"合同状态{contract.get('status')}，失效日{effective_to or '未设置'}，"
                f"超出效期的结算记录{len(invalid_rows)}条"
            ),
        }

    def check_review_sla(novel_id: str, request: str = "") -> dict[str, Any]:
        novel = repo.novel(novel_id)
        events = repo.workflow(novel_id)
        ai_passed = next(
            (event for event in events if event["state"] == "ai_review_passed"), None
        )
        editor_done = any(event["state"] == "editor_review_passed" for event in events)
        business_days = 0
        if ai_passed and not editor_done:
            raw_at = ai_passed.get("occurred_at") or ai_passed.get("at")
            passed_date = datetime.fromisoformat(raw_at).date()
            cursor = passed_date
            today = date.today()
            while cursor < today:
                cursor = date.fromordinal(cursor.toordinal() + 1)
                if cursor.weekday() < 5:
                    business_days += 1
        in_editor_review = novel.get("status") == "editor_review"
        detected = bool(
            in_editor_review and ai_passed and not editor_done and business_days > 3
        )
        return {
            "detected": detected,
            "anomaly_type": "editor_review_overdue" if detected else "none",
            "risk_level": "medium" if detected else "low",
            "affected_amount": 0,
            "business_days_elapsed": business_days,
            "conclusion": (
                "AI预审通过后超过3个工作日，仍未完成编辑复审。"
                if detected
                else "编辑复审未超过当前SLA。"
            ),
            "recommendation": "提醒负责编辑并转入超时队列，记录超时原因。",
            "evidence": (
                f"当前状态={novel.get('status')}，AI预审通过={bool(ai_passed)}，"
                f"编辑复审完成={editor_done}，"
                f"已过工作日={business_days}"
            ),
        }

    return {
        "get_novel_context": get_novel_context,
        "get_contract_terms": get_contract_terms,
        "get_settlement_summary": get_settlement_summary,
        "retrieve_policy": retrieve_policy,
        "check_settlement_consistency": check_settlement_consistency,
        "check_missing_settlement": check_missing_settlement,
        "check_duplicate_settlement": check_duplicate_settlement,
        "check_contract_validity": check_contract_validity,
        "check_review_sla": check_review_sla,
    }


def _build_default_hybrid_retriever(
    knowledge: KnowledgeBase,
) -> HybridRetriever | None:
    embedding_key = os.getenv("EMBEDDING_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
    embedding_url = os.getenv("EMBEDDING_BASE_URL") or os.getenv("DASHSCOPE_BASE_URL")
    if not embedding_key or not embedding_url:
        return None
    index = JsonVectorIndex()
    if not index.exists:
        return None
    provider = OpenAIEmbeddingProvider()
    rerank_enabled = os.getenv("HYBRID_RERANK_ENABLED", "true").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    llm_key = os.getenv("LLM_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
    llm_url = os.getenv("LLM_BASE_URL") or os.getenv("DASHSCOPE_BASE_URL")
    reranker = OpenAIReranker() if rerank_enabled and llm_key and llm_url else None
    return HybridRetriever(knowledge, index, provider, reranker)
