from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


_CJK_RE = re.compile(r"[\u4e00-\u9fff]+")
_WORD_RE = re.compile(r"[a-zA-Z0-9_.%-]+")
_HEADING_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)


def tokenize(text: str) -> list[str]:
    """Tokenize Chinese with characters and bigrams, plus Latin words."""
    normalized = text.lower()
    tokens = _WORD_RE.findall(normalized)
    for sequence in _CJK_RE.findall(normalized):
        tokens.extend(sequence)
        tokens.extend(sequence[index : index + 2] for index in range(len(sequence) - 1))
    return tokens


@dataclass(frozen=True)
class KnowledgeChunk:
    chunk_id: str
    document_id: str
    title: str
    section: str
    text: str
    metadata: dict[str, Any]


def _split_markdown(document: dict[str, Any], content: str) -> list[KnowledgeChunk]:
    matches = list(_HEADING_RE.finditer(content))
    chunks: list[KnowledgeChunk] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        section = match.group(1).strip()
        body = content[start:end].strip()
        if body:
            chunks.append(
                KnowledgeChunk(
                    chunk_id=f"{document['id']}#{index + 1}",
                    document_id=document["id"],
                    title=document["title"],
                    section=section,
                    text=body,
                    metadata={key: value for key, value in document.items() if key != "path"},
                )
            )
    return chunks


class KnowledgeBase:
    """Local BM25 knowledge base with business and effective-date filters."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path(__file__).resolve().parents[1] / "knowledge"
        catalog = json.loads((self.root / "catalog.json").read_text(encoding="utf-8"))
        self.chunks: list[KnowledgeChunk] = []
        for document in catalog:
            content = (self.root / document["path"]).read_text(encoding="utf-8")
            self.chunks.extend(_split_markdown(document, content))
        self._tokens = [tokenize(f"{chunk.title} {chunk.section} {chunk.text}") for chunk in self.chunks]
        self._term_frequencies = [Counter(tokens) for tokens in self._tokens]
        self._average_length = sum(map(len, self._tokens)) / max(len(self._tokens), 1)
        self._document_frequency = Counter()
        for tokens in self._tokens:
            self._document_frequency.update(set(tokens))

    def search(
        self,
        query: str,
        *,
        business_type: str | None = None,
        platform: str | None = None,
        effective_at: str | None = None,
        top_k: int = 3,
    ) -> list[dict[str, Any]]:
        query_tokens = tokenize(query)
        scored: list[tuple[float, KnowledgeChunk]] = []
        for index, chunk in self.eligible_chunks(
            business_type=business_type,
            platform=platform,
            effective_at=effective_at,
        ):
            score = self._bm25(query_tokens, index)
            if score > 0:
                scored.append((score, chunk))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [self.serialize_chunk(chunk, score=score) for score, chunk in scored[:top_k]]

    def eligible_chunks(
        self,
        *,
        business_type: str | None = None,
        platform: str | None = None,
        effective_at: str | None = None,
    ) -> list[tuple[int, KnowledgeChunk]]:
        eligible: list[tuple[int, KnowledgeChunk]] = []
        for index, chunk in enumerate(self.chunks):
            if business_type and chunk.metadata["business_type"] != business_type:
                continue
            if platform and chunk.metadata.get("platform") not in {platform, "cross_platform"}:
                continue
            if effective_at and not self._effective_on(chunk.metadata, effective_at):
                continue
            eligible.append((index, chunk))
        return eligible

    @staticmethod
    def _effective_on(metadata: dict[str, Any], date: str) -> bool:
        start = metadata.get("effective_from")
        starts_before = start is None or start <= date
        end = metadata.get("effective_to")
        return starts_before and (end is None or date <= end)

    def _bm25(self, query_tokens: list[str], index: int) -> float:
        k1, b = 1.5, 0.75
        frequencies = self._term_frequencies[index]
        length = len(self._tokens[index])
        corpus_size = len(self.chunks)
        score = 0.0
        for token in set(query_tokens):
            frequency = frequencies.get(token, 0)
            if not frequency:
                continue
            document_frequency = self._document_frequency[token]
            inverse_frequency = math.log(
                1 + (corpus_size - document_frequency + 0.5) / (document_frequency + 0.5)
            )
            denominator = frequency + k1 * (
                1 - b + b * length / max(self._average_length, 1)
            )
            score += inverse_frequency * frequency * (k1 + 1) / denominator
        return score

    @staticmethod
    def serialize_chunk(chunk: KnowledgeChunk, score: float = 0.0) -> dict[str, Any]:
        return {
            "chunk_id": chunk.chunk_id,
            "score": round(score, 4),
            "citation": f"《{chunk.title}》{chunk.metadata['version']} {chunk.section}",
            "text": chunk.text,
            "document_id": chunk.document_id,
            "section": chunk.section,
            "version": chunk.metadata["version"],
            "effective_from": chunk.metadata["effective_from"],
            "effective_to": chunk.metadata.get("effective_to"),
            "business_type": chunk.metadata["business_type"],
            "platform": chunk.metadata.get("platform"),
            "source_type": chunk.metadata.get("source_type", "unknown"),
            "verification_status": chunk.metadata.get("verification_status", "unknown"),
            "source_url": chunk.metadata.get("source_url", ""),
        }

    @staticmethod
    def embedding_text(chunk: KnowledgeChunk) -> str:
        return "\n".join(
            [
                f"平台：{chunk.metadata.get('platform', '')}",
                f"文档：{chunk.title}",
                f"条款：{chunk.section}",
                f"正文：{chunk.text}",
            ]
        )
