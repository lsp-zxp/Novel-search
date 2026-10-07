from __future__ import annotations

from novelops_agent.schemas import IntentClassification


def classify_intent_locally(request: str) -> IntentClassification:
    """Deterministic fallback used offline or when the online classifier fails."""
    text = request.lower()
    groups = {
        "settlement_audit": ("结算", "稿费", "金额", "分成", "账单", "漏单", "重复付款"),
        "contract_audit": ("合同", "签约", "生效", "失效", "到期", "授权"),
        "review_sla": ("审核", "复审", "超时", "卡住", "时效", "低质"),
    }
    policy_words = ("规则", "制度", "办法", "门槛", "规定", "多少", "需要多少")
    audit_words = ("检查", "核对", "异常", "调查", "为什么", "是否", "超时", "到期", "漏单", "重复")
    matched = [
        name for name, keywords in groups.items() if any(word in text for word in keywords)
    ]
    if any(word in text for word in policy_words) and not any(
        word in text for word in audit_words
    ):
        intent = "policy_lookup"
        reason = "请求只询问制度、门槛或具体规定"
        confidence = 0.9
    elif any(word in text for word in ("全面", "全量", "整体", "全部流程")) or len(matched) > 1:
        intent = "full_audit"
        reason = "请求要求全面检查或同时涉及多个业务领域"
        confidence = 0.95
    elif matched:
        intent = matched[0]
        reason = f"请求命中{intent}场景关键词"
        confidence = 0.9
    elif any(word in text for word in policy_words):
        intent = "policy_lookup"
        reason = "请求主要询问制度或规则"
        confidence = 0.85
    else:
        intent = "full_audit"
        reason = "请求边界不明确，使用全量巡检兜底"
        confidence = 0.6
    return IntentClassification(
        intent=intent,
        confidence=confidence,
        normalized_request=request.strip(),
        reason=reason,
        source="rule_fallback",
    )
