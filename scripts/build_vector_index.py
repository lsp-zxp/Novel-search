from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from novelops_agent.embeddings import OpenAIEmbeddingProvider
from novelops_agent.rag import KnowledgeBase
from novelops_agent.vector_index import JsonVectorIndex


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="构建或增量更新本地JSON向量索引")
    parser.add_argument("--force", action="store_true", help="忽略缓存，重建全部向量")
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--model", default=None)
    parser.add_argument("--dimensions", type=int, default=None)
    args = parser.parse_args()

    knowledge = KnowledgeBase()
    provider = OpenAIEmbeddingProvider(model=args.model, dimensions=args.dimensions)
    index = JsonVectorIndex()
    result = index.build(
        knowledge,
        provider,
        batch_size=args.batch_size,
        force=args.force,
    )
    print(
        json.dumps(
            {
                "index": str(index.path),
                "model": provider.model,
                "dimensions": provider.dimensions,
                **result,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
