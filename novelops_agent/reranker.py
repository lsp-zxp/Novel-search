from __future__ import annotations

import json
import os
from typing import Protocol

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()


class Reranker(Protocol):
    def rerank(
        self, query: str, candidates: list[dict], *, top_k: int
    ) -> list[dict]: ...


class RerankJudgment(BaseModel):
    chunk_id: str
    relevance_score: int = Field(ge=0, le=100)
    reason: str


class RerankResponse(BaseModel):
    results: list[RerankJudgment]


class OpenAICompatibleReranker:
    """Listwise reranker over an OpenAI-compatible Chat Completions endpoint."""

    def __init__(
        self,
        *,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        from openai import OpenAI

        key = api_key or os.getenv("LLM_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
        endpoint = base_url or os.getenv("LLM_BASE_URL") or os.getenv("DASHSCOPE_BASE_URL")
        if not key:
            raise RuntimeError("缺少 LLM_API_KEY 或 DASHSCOPE_API_KEY，无法执行在线Rerank。")
        if not endpoint:
            raise RuntimeError("缺少 LLM_BASE_URL 或 DASHSCOPE_BASE_URL，无法执行在线Rerank。")
        self.model = model or os.getenv("RERANK_MODEL", "deepseek-v4-pro")
        self.base_url = endpoint
        self._client = OpenAI(api_key=key, base_url=endpoint)

    def rerank(
        self, query: str, candidates: list[dict], *, top_k: int
    ) -> list[dict]:
        if not candidates:
            return []
        compact_candidates = [
            {
                "chunk_id": item["chunk_id"],
                "platform": item.get("platform"),
                "title": item.get("citation"),
                "text": item.get("text"),
                "verification_status": item.get("verification_status"),
            }
            for item in candidates
        ]
        completion = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是小说业务规则检索的重排序器。只评估候选条款对查询的直接支持程度。"
                        "精确平台、数字、时间条件和规则原文优先。必须只返回JSON对象，格式为"
                        '{"results":[{"chunk_id":"候选ID","relevance_score":0到100整数,'
                        '"reason":"简短理由"}]}。不得创造候选中不存在的ID。'
                        "必须对每个候选ID恰好输出一条评分，即使候选不相关也必须评分，"
                        "results数量必须与候选数量完全一致。"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"查询：{query}\n"
                        f"候选条款：{json.dumps(compact_candidates, ensure_ascii=False)}"
                    ),
                },
            ],
            response_format={"type": "json_object"},
            extra_body={"enable_thinking": False},
        )
        content = completion.choices[0].message.content or ""
        try:
            parsed = RerankResponse.model_validate_json(content)
        except Exception as exc:
            raise RuntimeError(f"Rerank模型返回的JSON无法解析：{exc}") from exc

        candidate_map = {item["chunk_id"]: item for item in candidates}
        valid: list[dict] = []
        seen: set[str] = set()
        for judgment in sorted(
            parsed.results, key=lambda item: item.relevance_score, reverse=True
        ):
            if judgment.chunk_id not in candidate_map or judgment.chunk_id in seen:
                continue
            seen.add(judgment.chunk_id)
            valid.append(
                {
                    **candidate_map[judgment.chunk_id],
                    "rerank_score": judgment.relevance_score,
                    "rerank_reason": judgment.reason,
                }
            )
        for item in candidates:
            if item["chunk_id"] not in seen:
                valid.append({**item, "rerank_score": None, "rerank_reason": "模型未返回该候选"})
        return valid[:top_k]


OpenAIReranker = OpenAICompatibleReranker
