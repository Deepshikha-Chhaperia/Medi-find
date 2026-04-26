"""
Agent 6: Retrieval Agent
Embeds queries using sentence-transformers, searches PostgreSQL pgvector, applies filters.
"""
from __future__ import annotations
import os
import math
import re
import hashlib
from functools import lru_cache
from db.database import semantic_search

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None  # type: ignore[assignment]

_MODEL_NAME = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
_DISABLE_LOCAL_MODELS = os.getenv("DISABLE_LOCAL_MODELS", "false").lower() == "true"
_EMBED_DIM = 384


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    if _DISABLE_LOCAL_MODELS or SentenceTransformer is None:
        raise RuntimeError("Local embedding model unavailable")
    print(f"[Retrieval] Loading embedding model: {_MODEL_NAME}")
    return SentenceTransformer(_MODEL_NAME)


def _fallback_embed(text: str) -> list[float]:
    """Deterministic hashed embedding fallback for serverless mode."""
    vec = [0.0] * _EMBED_DIM
    tokens = re.findall(r"[a-z0-9_]+", (text or "").lower())
    if not tokens:
        return vec

    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:2], "big") % _EMBED_DIM
        sign = 1.0 if (digest[2] % 2 == 0) else -1.0
        vec[idx] += sign

    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


def embed(text: str) -> list[float]:
    """Embed a single string. Returns 384-dim float list."""
    try:
        model = _get_model()
        vec = model.encode(text, normalize_embeddings=True)
        return vec.tolist()
    except Exception:
        return _fallback_embed(text)


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed multiple strings in one forward pass (efficient)."""
    try:
        model = _get_model()
        return model.encode(texts, normalize_embeddings=True, batch_size=32).tolist()
    except Exception:
        return [_fallback_embed(t) for t in texts]


def _retrieve_lexical(
    conn,
    query_text: str,
    n_per_query: int,
    state: str | None,
    district: str | None,
    emergency_only: bool,
    capabilities_filter: list[str] | None,
) -> list[dict]:
    """Fallback lexical retrieval for serverless-friendly deployments."""
    terms = [t.strip().lower() for t in query_text.split() if len(t.strip()) > 2][:8]
    filters = []
    params: list[object] = []

    if state:
        filters.append("c.state = %s")
        params.append(state)
    if district:
        filters.append("c.district = %s")
        params.append(district)
    if emergency_only:
        filters.append("c.emergency_24x7 = TRUE")
    if capabilities_filter:
        filters.append("c.capabilities && %s::text[]")
        params.append(capabilities_filter)

    if terms:
        text_predicates = ["LOWER(c.chunk_text) LIKE %s" for _ in terms]
        filters.append("(" + " OR ".join(text_predicates) + ")")
        params.extend([f"%{t}%" for t in terms])

    where_sql = ("WHERE " + " AND ".join(filters)) if filters else ""
    sql = f"""
        SELECT c.chunk_id, c.doc_id, c.facility_id, c.chunk_text,
               c.facility_name, c.state, c.district, c.facility_type,
               c.emergency_24x7, c.capabilities,
               f.data_age_days,
               0.55 AS similarity
        FROM chunks c
        LEFT JOIN facilities f ON f.facility_id = c.facility_id
        {where_sql}
        ORDER BY c.created_at DESC
        LIMIT {n_per_query}
    """
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]


def retrieve(
    conn,
    sub_queries: list[str],
    n_per_query: int = 20,
    state: str | None = None,
    district: str | None = None,
    emergency_only: bool = False,
    capabilities_filter: list[str] | None = None,
) -> list[dict]:
    """
    Embed each sub-query and search pgvector. Merge + deduplicate by chunk_id.
    Returns up to n_per_query * len(sub_queries) unique chunks, sorted by best similarity.
    """
    all_chunks: dict[str, dict] = {}
    use_lexical = _DISABLE_LOCAL_MODELS or SentenceTransformer is None

    for sq in sub_queries:
        if use_lexical:
            chunks = _retrieve_lexical(
                conn,
                query_text=sq,
                n_per_query=n_per_query,
                state=state,
                district=district,
                emergency_only=emergency_only,
                capabilities_filter=capabilities_filter,
            )
        else:
            embedding = embed(sq)
            chunks = semantic_search(
                conn,
                query_embedding=embedding,
                n_results=n_per_query,
                state=state,
                district=district,
                emergency_only=emergency_only,
                capabilities_filter=capabilities_filter,
            )
        for chunk in chunks:
            cid = str(chunk["chunk_id"])
            if cid not in all_chunks or all_chunks[cid]["similarity"] < chunk["similarity"]:
                all_chunks[cid] = chunk

    return sorted(all_chunks.values(), key=lambda x: x["similarity"], reverse=True)[:30]
