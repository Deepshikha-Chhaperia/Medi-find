"""
MediFind — SQLite Database Layer.
Replaces PostgreSQL + pgvector for zero-setup local development.
"""
from __future__ import annotations

import os
import json
import sqlite3
import numpy as np
from contextlib import contextmanager
from typing import Generator, Any
from dotenv import load_dotenv

_HERE = os.path.dirname(__file__)
load_dotenv(os.path.normpath(os.path.join(_HERE, "..", ".env")))
load_dotenv(os.path.normpath(os.path.join(_HERE, "..", "..", ".env")))
load_dotenv()

DB_PATH = os.path.join(_HERE, "medifind.db")

def get_connection() -> sqlite3.Connection:
    """Get a raw sqlite3 connection with row factory set to dict-like."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Enable Foreign Keys
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Yield a sqlite3 connection. Auto-commits on exit."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db() -> None:
    """Create all tables and indexes from schema.sqlite.sql (idempotent)."""
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sqlite.sql")
    with open(schema_path, "r", encoding="utf-8") as f:
        sql = f.read()
    with get_db() as conn:
        conn.executescript(sql)
    print(f"[DB] SQLite initialised at {DB_PATH} ✓")

# ─── Generic helpers ─────────────────────────────────────────────────────────

def _fix_sql(sql: str) -> str:
    """Replace PostgreSQL specific syntax with SQLite compatibility."""
    sql = sql.replace("%s", "?")
    sql = sql.replace("NOW()", "CURRENT_TIMESTAMP")
    sql = sql.replace("now()", "CURRENT_TIMESTAMP")
    sql = sql.replace("uuid_generate_v4()", "(lower(hex(randomblob(16))))") # Mock UUID if used
    return sql

def fetchone(conn: sqlite3.Connection, sql: str, params=None) -> dict | None:
    cur = conn.execute(_fix_sql(sql), params or ())
    row = cur.fetchone()
    return dict(row) if row else None

def fetchall(conn: sqlite3.Connection, sql: str, params=None) -> list[dict]:
    cur = conn.execute(_fix_sql(sql), params or ())
    return [dict(r) for r in cur.fetchall()]

def execute(conn: sqlite3.Connection, sql: str, params=None) -> None:
    # If params is a dict, we don't replace %s (we use :named)
    if isinstance(params, dict):
        conn.execute(sql, params)
    else:
        conn.execute(_fix_sql(sql), params or ())

def executemany(conn: sqlite3.Connection, sql: str, param_list: list) -> None:
    conn.executemany(_fix_sql(sql), param_list)

def insert_returning(conn: sqlite3.Connection, sql: str, params=None) -> dict | None:
    """SQLite doesn't always support RETURNING (v<3.35). We use it if present, or fallback."""
    try:
        cur = conn.execute(sql, params or ())
        row = cur.fetchone()
        return dict(row) if row else None
    except sqlite3.OperationalError as e:
        # Fallback if RETURNING fails (unlikely in modern sqlite but safe)
        if "RETURNING" in sql.upper():
            clean_sql = sql.split("RETURNING")[0]
            cur = conn.execute(clean_sql, params or ())
            # This fallback is tricky for non-serial PKs.
            # Most of our tables use UUID (TEXT) anyway.
            return None
        raise

# ─── Facility helpers ──────────────────────────────────────────────────────────

def upsert_facility(conn: sqlite3.Connection, data: dict) -> str:
    """Insert or update a facility. Returns facility_id."""
    # Ensure JSON serializable fields
    data_copy = data.copy()
    if isinstance(data_copy.get("accreditations"), list):
        data_copy["accreditations"] = json.dumps(data_copy["accreditations"])
    if isinstance(data_copy.get("trust_flags"), list):
        data_copy["trust_flags"] = json.dumps(data_copy["trust_flags"])

    sql = """
    INSERT INTO facilities (
        facility_id, facility_name, facility_name_normalized, facility_type,
        address, pin_code, state, district, city, lat, lng, geocoded,
        contact_phone, contact_email, website, emergency_24x7,
        total_beds, icu_beds, nicu_beds, accreditations, operational_hours,
        source_doc_id, source_excerpt, extraction_confidence, trust_score,
        trust_flags, data_age_days
    ) VALUES (
        :facility_id, :facility_name, :facility_name_normalized, :facility_type,
        :address, :pin_code, :state, :district, :city,
        :lat, :lng, :geocoded,
        :contact_phone, :contact_email, :website, :emergency_24x7,
        :total_beds, :icu_beds, :nicu_beds, :accreditations,
        :operational_hours, :source_doc_id, :source_excerpt,
        :extraction_confidence, :trust_score, :trust_flags, :data_age_days
    )
    ON CONFLICT (facility_id) DO UPDATE SET
        facility_name = excluded.facility_name,
        extraction_confidence = excluded.extraction_confidence,
        trust_score = excluded.trust_score,
        trust_flags = excluded.trust_flags,
        updated_at = CURRENT_TIMESTAMP
    """
    execute(conn, sql, data_copy)
    return data["facility_id"]

def upsert_capabilities(conn: sqlite3.Connection, facility_id: str, caps: list[dict]) -> None:
    if not caps:
        return
    sql = """
    INSERT INTO facility_capabilities (facility_id, capability_id, capability_name, raw_extracted_text, confidence)
    VALUES (?, ?, ?, ?, ?)
    ON CONFLICT (facility_id, capability_id) DO UPDATE SET
        confidence = excluded.confidence
    """
    executemany(conn, sql, [
        (facility_id, c["capability_id"], c["capability_name"],
         c.get("raw_extracted_text", ""), c.get("confidence", 0.7))
        for c in caps
    ])

def upsert_equipment(conn: sqlite3.Connection, facility_id: str, equipment_names: list[str]) -> None:
    if not equipment_names:
        return
    sql = """
    INSERT INTO facility_equipment (facility_id, equipment_name, equipment_canonical, quantity)
    VALUES (?, ?, ?, ?)
    """
    cleaned = [(facility_id, e.strip(), e.strip().lower(), None) for e in equipment_names if e and e.strip()]
    if not cleaned:
        return
    executemany(conn, sql, cleaned)

# ─── Chunk / embedding helpers ────────────────────────────────────────────────

def upsert_chunk(conn: sqlite3.Connection, chunk: dict) -> None:
    """Store a chunk with its embedding vector (as JSON)."""
    chunk_copy = chunk.copy()
    if isinstance(chunk_copy.get("embedding"), (list, np.ndarray)):
        chunk_copy["embedding"] = json.dumps(list(chunk_copy["embedding"]))
    if isinstance(chunk_copy.get("capabilities"), list):
        chunk_copy["capabilities"] = json.dumps(chunk_copy["capabilities"])

    sql = """
    INSERT INTO chunks (
        chunk_id, doc_id, facility_id, chunk_text, chunk_index, page_number,
        token_count, embedding, facility_name, state, district,
        facility_type, emergency_24x7, capabilities
    ) VALUES (
        :chunk_id, :doc_id, :facility_id, :chunk_text,
        :chunk_index, :page_number, :token_count, :embedding,
        :facility_name, :state, :district,
        :facility_type, :emergency_24x7, :capabilities
    )
    ON CONFLICT (chunk_id) DO NOTHING
    """
    execute(conn, sql, chunk_copy)

def semantic_search(
    conn: sqlite3.Connection,
    query_embedding: list[float],
    n_results: int = 20,
    state: str | None = None,
    district: str | None = None,
    emergency_only: bool = False,
    capabilities_filter: list[str] | None = None,
) -> list[dict]:
    """
    Manual semantic search for SQLite. 
    Fetches candidate chunks and computes cosine similarity in Python.
    """
    filters = []
    params = []

    if state:
        filters.append("state = ?")
        params.append(state)
    if district:
        filters.append("district = ?")
        params.append(district)
    if emergency_only:
        filters.append("emergency_24x7 = 1")

    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    sql = f"SELECT * FROM chunks {where}"
    
    rows = fetchall(conn, sql, params)
    if not rows:
        return []

    # Manual Cosine Similarity
    query_vec = np.array(query_embedding)
    results = []

    for row in rows:
        try:
            chunk_vec = np.array(json.loads(row["embedding"]))
            # Similarity = (A . B) / (||A|| * ||B||)
            norm_a = np.linalg.norm(query_vec)
            norm_b = np.linalg.norm(chunk_vec)
            if norm_a == 0 or norm_b == 0:
                sim = 0.0
            else:
                sim = np.dot(query_vec, chunk_vec) / (norm_a * norm_b)
            
            # Application-level filter for capabilities (since SQLite 
            # doesn't have native array overlaps)
            if capabilities_filter:
                row_caps = json.loads(row["capabilities"] or "[]")
                if not any(c in row_caps for c in capabilities_filter):
                    continue

            row_dict = dict(row)
            row_dict["similarity"] = float(sim)
            # Rehydrate JSON fields
            row_dict["capabilities"] = json.loads(row_dict["capabilities"] or "[]")
            results.append(row_dict)
        except Exception:
            continue

    # Sort and slice
    results.sort(key=lambda x: x["similarity"], reverse=True)
    return results[:n_results]

# ─── Document helpers ─────────────────────────────────────────────────────────

def create_document(conn: sqlite3.Connection, data: dict) -> str:
    doc_id = str(data.get("doc_id") or os.urandom(8).hex())
    sql = """
    INSERT INTO documents (doc_id, source_file, file_type, file_size_kb, status)
    VALUES (?, ?, ?, ?, 'PENDING')
    """
    conn.execute(sql, (doc_id, data["source_file"], data["file_type"], data["file_size_kb"]))
    return doc_id

def update_document_status(conn: sqlite3.Connection, doc_id: str, status: str, error: str | None = None) -> None:
    sql = """
    UPDATE documents SET status = ?, error_message = ?, processed_at = CURRENT_TIMESTAMP
    WHERE doc_id = ?
    """
    conn.execute(sql, (status, error, doc_id))

# ─── Ingestion job helpers ────────────────────────────────────────────────────

def create_job(conn: sqlite3.Connection, total_files: int) -> str:
    job_id = os.urandom(8).hex()
    sql = "INSERT INTO ingestion_jobs (job_id, total_files) VALUES (?, ?)"
    conn.execute(sql, (job_id, total_files))
    return job_id

def update_job(conn: sqlite3.Connection, job_id: str, processed: int, failed: int, status: str = "RUNNING") -> None:
    sql = """
    UPDATE ingestion_jobs
    SET processed_files = ?, failed_files = ?, status = ?,
        completed_at = CASE WHEN ? != 'RUNNING' THEN CURRENT_TIMESTAMP ELSE NULL END
    WHERE job_id = ?
    """
    conn.execute(sql, (processed, failed, status, status, job_id))

# ─── Geocode cache ────────────────────────────────────────────────────────────

def get_cached_geocode(conn: sqlite3.Connection, address_key: str) -> tuple[float, float] | None:
    row = fetchone(conn, "SELECT lat, lng FROM geocode_cache WHERE address_key = ?", (address_key,))
    if row:
        return row["lat"], row["lng"]
    return None

def cache_geocode(conn: sqlite3.Connection, address_key: str, lat: float, lng: float) -> None:
    sql = """
    INSERT INTO geocode_cache (address_key, lat, lng)
    VALUES (?, ?, ?)
    ON CONFLICT (address_key) DO NOTHING
    """
    conn.execute(sql, (address_key, lat, lng))
