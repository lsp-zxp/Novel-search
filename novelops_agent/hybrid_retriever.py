from __future__ import annotations

from typing import Any

from novelops_agent.embeddings import EmbeddingProvider
from novelops_agent.rag import KnowledgeBase
from novelops_agent.reranker import Reranker
from novelops_agent.vector_index import JsonVectorIndex


class HybridRetriever:
    """BM25 + dense vectors + RRF + optional reranking."""

    def __init__(
        self,
        knowledge: KnowledgeBase,
        vector_index: JsonVectorIndex,
        embedding_provider: EmbeddingProvider,
        reranker: Reranker | None = None,
        *,
        rrf_k: int = 60,
    ) -> None:
        self.knowledge = knowledge
        self.vector_index = vector_index
        self.embedding_provider = embedding_provider
        self.reranker = reranker
        self.rrf_k = rrf_k

    def search(
        self,
        query: str,
        *,
        business_type: str | None = None,
        platform: str | None = None,
        effective_at: str | None = None,
        bm25_k: int = 20,
        vector_k: int = 20,
        fusion_k: int = 10,
        final_k: int = 3,
    ) -> list[dict[str, Any]]:
        self.vector_index.validate_provider(self.embedding_provider)
        bm25_results = self.knowledge.search(
            query,
            business_type=business_type,
            platform=platform,
            effective_at=effective_at,
            top_k=bm25_k,
        )
        query_vector = self.embedding_provider.embed_query(query)
        vector_results = self.vector_index.search(
            query_vector,
            knowledge=self.knowledge,
            business_type=business_type,
            platform=platform,
            effective_at=effective_at,
            top_k=vector_k,
        )
        fused = self._rrf_fuse(bm25_results, vector_results)[:fusion_k]
        if self.reranker:
            return self.reranker.rerank(query, fused, top_k=final_k)
        return fused[:final_k]

    def _rrf_fuse(
        self, bm25_results: list[dict[str, Any]], vector_results: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        merged: dict[str, dict[str, Any]] = {}
        for source, results in (("bm25", bm25_results), ("vector", vector_results)):
            for rank, result in enumerate(results, 1):
                chunk_id = result["chunk_id"]
                item = merged.setdefault(
                    chunk_id,
                    {
                        **result,
                        "rrf_score": 0.0,
                        "bm25_rank": None,
                        "vector_rank": None,
                        "bm25_score": None,
                        "vector_score": None,
                        "retrieval_sources": [],
                    },
                )
                item["rrf_score"] += 1.0 / (self.rrf_k + rank)
                item[f"{source}_rank"] = rank
                if source == "bm25":
                    item["bm25_score"] = result.get("score")
                else:
                    item["vector_score"] = result.get("vector_score")
                item["retrieval_sources"].append(source)
        output = list(merged.values())
        for item in output:
            item["rrf_score"] = round(item["rrf_score"], 8)
        output.sort(key=lambda item: item["rrf_score"], reverse=True)
        return output
