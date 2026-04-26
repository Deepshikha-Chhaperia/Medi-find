"""
Agent 7: Re-ranker
Uses cross-encoder ms-marco-MiniLM-L-6-v2 to re-score (query, chunk) pairs.
Final score = 0.4×vector + 0.4×cross-encoder + 0.2×recency.
"""
from __future__ import annotations
import os
import math
from functools import lru_cache

try:
    from sentence_transformers import CrossEncoder
except Exception:
    CrossEncoder = None  # type: ignore[assignment]

_RERANKER_MODEL = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
_DISABLE_LOCAL_MODELS = os.getenv("DISABLE_LOCAL_MODELS", "false").lower() == "true"


@lru_cache(maxsize=1)
def _get_reranker() -> CrossEncoder:
    if _DISABLE_LOCAL_MODELS or CrossEncoder is None:
        raise RuntimeError("Local reranker model unavailable")
    print(f"[Reranker] Loading cross-encoder: {_RERANKER_MODEL}")
    return CrossEncoder(_RERANKER_MODEL)


def _recency_score(data_age_days: int) -> float:
    """Higher score = more recent. Decays over 2 years."""
    return max(0.0, 1.0 - data_age_days / 730)


def rerank(
    query: str,
    candidates: list[dict],
    top_k: int = 15,
) -> list[dict]:
    """
    Re-rank candidates using cross-encoder + recency.
    Each candidate must have: chunk_text, similarity, data_age_days (optional).
    Returns top_k candidates with `final_score` added, sorted desc.
    """
    if not candidates:
        return []

    use_simple = _DISABLE_LOCAL_MODELS or CrossEncoder is None
    if not use_simple:
        reranker = _get_reranker()
        pairs = [(query, c.get("chunk_text", "")) for c in candidates]
        cross_scores_raw = reranker.predict(pairs)
        # Sigmoid-normalise cross encoder scores to [0, 1]
        cross_scores = [1 / (1 + math.exp(-s)) for s in cross_scores_raw]
    else:
        # Serverless-friendly fallback: rely on retrieval similarity + recency.
        cross_scores = [float(c.get("similarity", 0.5)) for c in candidates]

    scored = []
    for i, chunk in enumerate(candidates):
        vector_sim = float(chunk.get("similarity", 0.5))
        cross_sim = float(cross_scores[i])
        recency = _recency_score(chunk.get("data_age_days", 365))

        final = 0.4 * vector_sim + 0.4 * cross_sim + 0.2 * recency
        scored.append({**chunk, "cross_score": cross_sim, "final_score": round(final, 4)})

    scored.sort(key=lambda x: x["final_score"], reverse=True)
    return scored[:top_k]
