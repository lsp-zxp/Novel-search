from __future__ import annotations

import hashlib
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from novelops_agent.embeddings import EmbeddingProvider
from novelops_agent.rag import KnowledgeBase, KnowledgeChunk


def default_index_path() -> Path:
    configured = os.getenv("VECTOR_INDEX_PATH", "knowledge/index/vectors.json")
    path = Path(configured)
    if path.is_absolute():
        return path
    return Path(__file__).resolve().parents[1] / path


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _cosine(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError("查询向量与索引向量维度不一致。")
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


class JsonVectorIndex:
    SCHEMA_VERSION = 1

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_index_path()

    @property
    def exists(self) -> bool:
        return self.path.exists()

    def build(
        self,
        knowledge: KnowledgeBase,
        provider: EmbeddingProvider,
        *,
        batch_size: int = 32,
        force: bool = False,
    ) -> dict[str, int]:
        existing = self._load_optional()
        reusable: dict[str, dict[str, Any]] = {}
        if (
            not force
            and existing
            and existing.get("model") == provider.model
            and existing.get("dimensions") == provider.dimensions
        ):
            reusable = {record["chunk_id"]: record for record in existing["records"]}

        records: list[dict[str, Any]] = []
        pending: list[tuple[KnowledgeChunk, str, str]] = []
        reused_count = 0
        for chunk in knowledge.chunks:
            text = knowledge.embedding_text(chunk)
            digest = _content_hash(text)
            old = reusable.get(chunk.chunk_id)
            if old and old.get("content_hash") == digest:
                records.append(
                    {
                        **knowledge.serialize_chunk(chunk),
                        "embedding_text": text,
                        "content_hash": digest,
                        "vector": old["vector"],
                    }
                )
                reused_count += 1
            else:
                pending.append((chunk, text, digest))

        generated: list[dict[str, Any]] = []
        for offset in range(0, len(pending), batch_size):
            batch = pending[offset : offset + batch_size]
            vectors = provider.embed_documents([item[1] for item in batch])
            if len(vectors) != len(batch):
                raise RuntimeError("Embedding返回数量与输入Chunk数量不一致。")
            for (chunk, text, digest), vector in zip(batch, vectors):
                serialized = knowledge.serialize_chunk(chunk)
                generated.append(
                    {
                        **serialized,
                        "embedding_text": text,
                        "content_hash": digest,
                        "vector": vector,
                    }
                )

        records.extend(generated)
        records.sort(key=lambda record: record["chunk_id"])
        payload = {
            "schema_version": self.SCHEMA_VERSION,
            "model": provider.model,
            "dimensions": provider.dimensions,
            "built_at": datetime.now(timezone.utc).isoformat(),
            "records": records,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        temporary.replace(self.path)
        return {
            "total": len(records),
            "generated": len(generated),
            "reused": reused_count,
            "removed": max(len(reusable) - reused_count, 0),
        }

    def search(
        self,
        query_vector: list[float],
        *,
        knowledge: KnowledgeBase,
        business_type: str | None = None,
        platform: str | None = None,
        effective_at: str | None = None,
        top_k: int = 20,
    ) -> list[dict[str, Any]]:
        payload = self.load()
        if payload["dimensions"] != len(query_vector):
            raise ValueError(
                f"索引维度为{payload['dimensions']}，查询向量维度为{len(query_vector)}，请重建索引。"
            )
        eligible_ids = {
            chunk.chunk_id
            for _, chunk in knowledge.eligible_chunks(
                business_type=business_type,
                platform=platform,
                effective_at=effective_at,
            )
        }
        scored = []
        for record in payload["records"]:
            if record["chunk_id"] not in eligible_ids:
                continue
            item = {key: value for key, value in record.items() if key != "vector"}
            item["vector_score"] = round(_cosine(query_vector, record["vector"]), 6)
            scored.append(item)
        scored.sort(key=lambda item: item["vector_score"], reverse=True)
        return scored[:top_k]

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            raise FileNotFoundError(
                f"向量索引不存在：{self.path}。请先运行 scripts/build_vector_index.py。"
            )
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if payload.get("schema_version") != self.SCHEMA_VERSION:
            raise ValueError("向量索引版本不兼容，请重新构建。")
        return payload

    def validate_provider(self, provider: EmbeddingProvider) -> None:
        payload = self.load()
        if payload["model"] != provider.model:
            raise ValueError(
                f"索引模型为{payload['model']}，查询模型为{provider.model}，请重建索引。"
            )
        if payload["dimensions"] != provider.dimensions:
            raise ValueError(
                f"索引维度为{payload['dimensions']}，查询配置维度为{provider.dimensions}，请重建索引。"
            )

    def _load_optional(self) -> dict[str, Any] | None:
        if not self.path.exists():
            return None
        return self.load()
