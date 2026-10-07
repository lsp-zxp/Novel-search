from __future__ import annotations

import os
from typing import Protocol

from dotenv import load_dotenv

load_dotenv()


class EmbeddingProvider(Protocol):
    model: str
    dimensions: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class OpenAICompatibleEmbeddingProvider:
    """Online embedding provider for OpenAI-compatible endpoints such as Bailian."""

    def __init__(
        self,
        *,
        model: str | None = None,
        dimensions: int | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        batch_size: int | None = None,
    ) -> None:
        from openai import OpenAI

        self.model = model or os.getenv("EMBEDDING_MODEL", "text-embedding-v4")
        self.dimensions = dimensions or int(os.getenv("EMBEDDING_DIMENSIONS", "1024"))
        self.batch_size = batch_size or int(os.getenv("EMBEDDING_BATCH_SIZE", "10"))
        key = api_key or os.getenv("EMBEDDING_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
        endpoint = (
            base_url
            or os.getenv("EMBEDDING_BASE_URL")
            or os.getenv("DASHSCOPE_BASE_URL")
        )
        if not key:
            raise RuntimeError(
                "缺少 EMBEDDING_API_KEY 或 DASHSCOPE_API_KEY，无法生成在线Embedding。"
            )
        if not endpoint:
            raise RuntimeError(
                "缺少 EMBEDDING_BASE_URL 或 DASHSCOPE_BASE_URL，无法调用Embedding接口。"
            )
        if self.batch_size < 1:
            raise ValueError("EMBEDDING_BATCH_SIZE必须大于0。")
        self.base_url = endpoint
        self._client = OpenAI(api_key=key, base_url=endpoint)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for offset in range(0, len(texts), self.batch_size):
            batch = texts[offset : offset + self.batch_size]
            if not batch:
                continue
            response = self._client.embeddings.create(
                model=self.model,
                input=batch,
                dimensions=self.dimensions,
                encoding_format="float",
            )
            vectors.extend(
                item.embedding for item in sorted(response.data, key=lambda item: item.index)
            )
        return vectors

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


OpenAIEmbeddingProvider = OpenAICompatibleEmbeddingProvider
