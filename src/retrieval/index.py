"""Hybrid retrieval: BM25 (lexical) + local fastembed embeddings (semantic).

No embeddings API — `fastembed` runs BAAI/bge-small-en-v1.5 on CPU (Rule 1).

Authority-aware gating:
- Deprecated docs are excluded unless `include_deprecated=True` (set only for
  explicit "what changed between versions" queries).
- Contract passages are scoped: visible only to their bound account, or to
  internal_ops. A customer never retrieves another account's contract.
Results are ordered by hybrid relevance; each carries its authority tier so the
agent can weigh sources correctly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from rank_bm25 import BM25Okapi

from src.config import get_settings
from src.domain.sources import Tier

from .chunks import Chunk, all_chunks

_TOKEN = re.compile(r"[a-z0-9]+")

# Queries that legitimately need the deprecated policy.
_VERSION_QUERY = re.compile(
    r"\b(v2|version 2|deprecated|what changed|changed between|previous policy|old policy)\b",
    re.I,
)


def wants_version_history(query: str) -> bool:
    return bool(_VERSION_QUERY.search(query))


def _tok(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


def _minmax(scores: np.ndarray) -> np.ndarray:
    lo, hi = scores.min(), scores.max()
    if hi - lo < 1e-9:
        return np.zeros_like(scores)
    return (scores - lo) / (hi - lo)


@dataclass(frozen=True)
class Hit:
    chunk: Chunk
    score: float


@lru_cache(maxsize=1)
def _embedder():
    from fastembed import TextEmbedding

    return TextEmbedding(model_name=get_settings().embedding_model)


class HybridIndex:
    def __init__(self, chunks: list[Chunk] | None = None) -> None:
        self.chunks = chunks or all_chunks()
        self._bm25 = BM25Okapi([_tok(c.text) for c in self.chunks])
        vecs = np.array(list(_embedder().embed([c.text for c in self.chunks])))
        # L2-normalize so dot product == cosine similarity.
        self._emb = vecs / (np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-9)

    def _visible(self, chunk: Chunk, account_id: str | None, is_internal: bool,
                 include_deprecated: bool) -> bool:
        if chunk.tier == int(Tier.DEPRECATED) and not include_deprecated:
            return False
        if chunk.tier == int(Tier.CONTRACT):
            if is_internal:
                return True
            return chunk.account_id == account_id
        return True

    def search(
        self,
        query: str,
        *,
        account_id: str | None = None,
        is_internal: bool = False,
        include_deprecated: bool = False,
        top_k: int = 5,
        alpha: float = 0.5,
    ) -> list[Hit]:
        """alpha weights semantic vs lexical (0=BM25 only, 1=embeddings only)."""
        bm = np.array(self._bm25.get_scores(_tok(query)))
        q = np.array(list(_embedder().embed([query])))[0]
        q = q / (np.linalg.norm(q) + 1e-9)
        cos = self._emb @ q
        hybrid = alpha * _minmax(cos) + (1 - alpha) * _minmax(bm)

        order = np.argsort(-hybrid)
        hits: list[Hit] = []
        for i in order:
            c = self.chunks[i]
            if not self._visible(c, account_id, is_internal, include_deprecated):
                continue
            hits.append(Hit(c, float(hybrid[i])))
            if len(hits) >= top_k:
                break
        return hits


@lru_cache(maxsize=1)
def get_index() -> HybridIndex:
    return HybridIndex()
