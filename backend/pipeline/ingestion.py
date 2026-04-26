"""
Ingestion Pipeline Orchestrator
Runs the full 8-step pipeline for a batch of files:
Parser → Chunker → Extractor → Normalizer → Embedder → Geocoder → DB write
"""
from __future__ import annotations
import os
import uuid
from pathlib import Path

from db.database import (
    get_db, create_document, update_document_status,
    upsert_facility, upsert_capabilities, upsert_equipment, upsert_chunk, update_job,
)
from agents.parser_agent import parse_file
from agents.chunker_agent import chunk_document
from agents.extractor_agent import extract_entities
from agents.normalizer_agent import normalize_capabilities, extract_capability_ids
from agents.retrieval_agent import embed_batch
from utils.geocoding import geocode_address


def ingest_file(file_path: str, job_id: str | None = None, conn=None) -> dict:
    """
    Run the full ingestion pipeline for a single file.
    Returns a status dict {status, facility_id, facility_name, error}.
    """
    path = Path(file_path)
    close_conn = False

    if conn is None:
        from db.database import get_db as _get
        ctx = _get()
        conn = ctx.__enter__()
        close_conn = True

    try:
        # ── Step 1: Register document ─────────────────────────────────────
        doc_id = create_document(conn, {
            "source_file": path.name,
            "file_type": path.suffix.lstrip("."),
            "file_size_kb": path.stat().st_size / 1024,
        })
        print(f"[Ingest] {path.name} → doc_id={doc_id}")

        # ── Step 2: Parse ─────────────────────────────────────────────────
        parsed = parse_file(file_path)
        parsed["doc_id"] = doc_id
        if not parsed.get("raw_text", "").strip():
            update_document_status(conn, doc_id, "FAILED", "Empty text after extraction")
            return {"status": "failed", "error": "Empty text"}
        update_document_status(conn, doc_id, "EXTRACTED")

        # ── Step 3: Chunk ─────────────────────────────────────────────────
        chunks = chunk_document(parsed)
        if not chunks:
            update_document_status(conn, doc_id, "FAILED", "No chunks produced")
            return {"status": "failed", "error": "No chunks"}
        update_document_status(conn, doc_id, "CHUNKED")

        # ── Step 4: Extract entities (Groq LLM) ───────────────────────────
        facility_data = extract_entities(parsed)
        if not facility_data or not facility_data.get("facility_name"):
            update_document_status(conn, doc_id, "FAILED", "Entity extraction returned empty")
            return {"status": "failed", "error": "No entities extracted"}
            
        # ── Step 4b: Trust Scorer Validation ──────────────────────────────
        from agents.validator_agent import ValidatorAgent
        validator = ValidatorAgent()
        facility_data = validator.run(facility_data, raw_text=parsed.get("raw_text"))
        
        update_document_status(conn, doc_id, "ENTITIES_EXTRACTED")

        # ── Step 5: Normalize capabilities ────────────────────────────────
        raw_specialties = facility_data.pop("_raw_specialties", [])
        raw_departments = facility_data.pop("_raw_departments", [])
        raw_equipment = facility_data.pop("_raw_equipment", [])
        raw_terms = raw_specialties + raw_departments + raw_equipment
        capabilities = normalize_capabilities(raw_terms)
        cap_ids = [c["capability_id"] for c in capabilities]
        update_document_status(conn, doc_id, "NORMALIZED")

        # ── Step 6: Geocode ───────────────────────────────────────────────
        if not facility_data.get("lat"):
            address_str = " ".join(filter(None, [
                facility_data.get("address"),
                facility_data.get("city"),
                facility_data.get("district"),
                facility_data.get("state"),
            ]))
            lat, lng = geocode_address(address_str, conn)
            facility_data["lat"] = lat
            facility_data["lng"] = lng
        facility_data["geocoded"] = bool(facility_data.get("lat"))
        facility_data.setdefault("data_age_days", 180)
        facility_data.setdefault("trust_score", 1.0)
        facility_data.setdefault("trust_flags", [])
        facility_data.setdefault("source_excerpt", parsed.get("raw_text", "")[:500])

        # ── Step 7: Write facility to DB ───────────────────────────────────
        fac_id = upsert_facility(conn, facility_data)
        upsert_capabilities(conn, fac_id, capabilities)
        upsert_equipment(conn, fac_id, raw_equipment)
        update_document_status(conn, doc_id, "GEOCODED")

        # ── Step 8: Embed chunks + write to DB ────────────────────────────
        texts = [c["chunk_text"] for c in chunks]
        embeddings = embed_batch(texts)
        for i, chunk in enumerate(chunks):
            chunk.update({
                "doc_id": doc_id,
                "facility_id": fac_id,
                "embedding": embeddings[i],
                "facility_name": facility_data.get("facility_name"),
                "state": facility_data.get("state"),
                "district": facility_data.get("district"),
                "facility_type": facility_data.get("facility_type"),
                "emergency_24x7": facility_data.get("emergency_24x7"),
                "capabilities": cap_ids,
            })
            upsert_chunk(conn, chunk)

        update_document_status(conn, doc_id, "COMPLETE")
        print(f"[Ingest] ✓ {facility_data['facility_name']} ({len(chunks)} chunks, {len(capabilities)} capabilities)")
        return {"status": "complete", "facility_id": fac_id, "facility_name": facility_data["facility_name"]}

    except Exception as e:
        print(f"[Ingest] ✗ {path.name}: {e}")
        return {"status": "failed", "error": str(e)}
    finally:
        if close_conn:
            ctx.__exit__(None, None, None)


def ingest_directory(directory: str, job_id: str | None = None) -> dict:
    """
    Ingest all supported files in a directory.
    Returns summary {total, completed, failed}.
    """
    SUPPORTED = {".pdf", ".csv", ".xlsx", ".xls", ".docx", ".txt", ".html", ".htm"}
    files = [
        str(p) for p in Path(directory).iterdir()
        if p.suffix.lower() in SUPPORTED and p.is_file()
    ]

    total = len(files)
    completed = 0
    failed = 0

    with get_db() as conn:
        if job_id:
            from db.database import update_job
            update_job(conn, job_id, 0, 0)

        for i, fpath in enumerate(files):
            result = ingest_file(fpath, job_id=job_id, conn=conn)
            if result.get("status") == "complete":
                completed += 1
            else:
                failed += 1

            if job_id:
                update_job(conn, job_id, completed + failed, failed,
                           "RUNNING" if i < total - 1 else "COMPLETE")

    return {"total": total, "completed": completed, "failed": failed}
