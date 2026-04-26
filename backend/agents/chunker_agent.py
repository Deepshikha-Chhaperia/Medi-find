"""
Agent 2: Semantic Chunker
Splits extracted text into retrieval-optimised chunks (200-400 tokens, 50 overlap).
"""
from __future__ import annotations
import uuid
from utils.text_utils import clean_text, chunk_text


def chunk_document(doc: dict) -> list[dict]:
    """
    Given a parsed document dict, return a list of chunk dicts ready for DB insertion.
    Each chunk: {chunk_id, doc_id, chunk_text, chunk_index, page_number, token_count}
    """
    raw = doc.get("raw_text", "")
    if not raw.strip():
        return []

    doc_id = doc["doc_id"]
    cleaned = clean_text(raw)
    raw_chunks = chunk_text(cleaned, target_tokens=300, overlap_tokens=50)

    return [
        {
            "chunk_id": str(uuid.uuid4()),
            "doc_id": doc_id,
            "facility_id": None,  # set after entity extraction
            "chunk_text": c["chunk_text"],
            "chunk_index": c["chunk_index"],
            "page_number": c.get("page_number", 1),
            "token_count": c["token_count"],
            "embedding": None,  # set by retrieval agent
            "facility_name": None,
            "state": None,
            "district": None,
            "facility_type": None,
            "emergency_24x7": None,
            "capabilities": [],
        }
        for c in raw_chunks
    ]
