from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from novelops_agent.embeddings import OpenAIEmbeddingProvider
from novelops_agent.hybrid_retriever import HybridRetriever
from novelops_agent.rag import KnowledgeBase
from novelops_agent.reranker import OpenAIReranker
from novelops_agent.vector_index import JsonVectorIndex


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="混合检索知识库")
    parser.add_argument("query")
    parser.add_argument("--platform", default=None)
    parser.add_argument("--business-type", default=None)
    parser.add_argument("--effective-at", default=None)
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--no-rerank", action="store_true")
    args = parser.parse_args()

    knowledge = KnowledgeBase()
    provider = OpenAIEmbeddingProvider()
    reranker = None if args.no_rerank else OpenAIReranker()
    retriever = HybridRetriever(
        knowledge,
        JsonVectorIndex(),
        provider,
        reranker,
    )
    results = retriever.search(
        args.query,
        platform=args.platform,
        business_type=args.business_type,
        effective_at=args.effective_at,
        final_k=args.top_k,
    )
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
