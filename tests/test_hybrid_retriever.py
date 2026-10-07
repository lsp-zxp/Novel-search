from pathlib import Path

import pytest

from novelops_agent.embeddings import OpenAIEmbeddingProvider
from novelops_agent.hybrid_retriever import HybridRetriever
from novelops_agent.rag import KnowledgeBase
from novelops_agent.vector_index import JsonVectorIndex


class FakeEmbeddingProvider:
    model = "fake-embedding-v1"
    dimensions = 3

    def __init__(self):
        self.document_calls = 0

    @staticmethod
    def _embed(text: str) -> list[float]:
        return [
            float("全勤" in text or "奖励" in text),
            float("合同" in text or "签约" in text),
            float("审核" in text or "低质" in text),
        ]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.document_calls += len(texts)
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


class PreferAttendanceReranker:
    def rerank(self, query: str, candidates: list[dict], *, top_k: int) -> list[dict]:
        ordered = sorted(
            candidates,
            key=lambda item: "fanqie-attendance-2026-10" in item["document_id"],
            reverse=True,
        )
        return [
            {**item, "rerank_score": 100 - index, "rerank_reason": "fake test rerank"}
            for index, item in enumerate(ordered[:top_k])
        ]


def build_test_index(tmp_path: Path):
    knowledge = KnowledgeBase()
    provider = FakeEmbeddingProvider()
    index = JsonVectorIndex(tmp_path / "vectors.json")
    stats = index.build(knowledge, provider, batch_size=7)
    return knowledge, provider, index, stats


def test_json_vector_index_builds_and_reuses_unchanged_chunks(tmp_path):
    knowledge, provider, index, stats = build_test_index(tmp_path)
    assert stats["total"] == len(knowledge.chunks)
    assert stats["generated"] == len(knowledge.chunks)
    assert index.exists

    second_provider = FakeEmbeddingProvider()
    second = index.build(knowledge, second_provider)
    assert second["generated"] == 0
    assert second["reused"] == len(knowledge.chunks)
    assert second_provider.document_calls == 0


def test_hybrid_retrieval_has_both_sources_and_rerank(tmp_path):
    knowledge, provider, index, _ = build_test_index(tmp_path)
    retriever = HybridRetriever(
        knowledge,
        index,
        provider,
        PreferAttendanceReranker(),
    )
    results = retriever.search(
        "签约一段时间后奖励收入有什么要求",
        business_type="settlement",
        platform="番茄小说",
        effective_at="2026-10-07",
        final_k=3,
    )
    assert results
    assert results[0]["document_id"] == "fanqie-attendance-2026-10"
    assert results[0]["rerank_score"] == 100
    assert any("vector" in item["retrieval_sources"] for item in results)
    assert all("rrf_score" in item for item in results)


def test_online_embedding_requires_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EMBEDDING_API_KEY", raising=False)
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="DASHSCOPE_API_KEY"):
        OpenAIEmbeddingProvider(api_key=None)


def test_bailian_embedding_defaults(monkeypatch):
    monkeypatch.delenv("EMBEDDING_MODEL", raising=False)
    monkeypatch.delenv("EMBEDDING_DIMENSIONS", raising=False)
    monkeypatch.delenv("EMBEDDING_BATCH_SIZE", raising=False)
    provider = OpenAIEmbeddingProvider(
        api_key="test-key",
        base_url="https://example.test/compatible-mode/v1",
    )
    assert provider.model == "text-embedding-v4"
    assert provider.dimensions == 1024
    assert provider.batch_size == 10


def test_rejects_query_provider_that_does_not_match_index(tmp_path):
    knowledge, _, index, _ = build_test_index(tmp_path)
    wrong_provider = FakeEmbeddingProvider()
    wrong_provider.model = "different-model"
    retriever = HybridRetriever(knowledge, index, wrong_provider)
    with pytest.raises(ValueError, match="索引模型"):
        retriever.search("全勤奖励")
