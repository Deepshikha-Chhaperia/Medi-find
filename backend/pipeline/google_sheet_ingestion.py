"""
Google Sheet ingestion for Hackathon dataset.
Fetches directly from the provided sheet URL and writes facilities/capabilities/chunks.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from io import StringIO
from typing import Any

import pandas as pd
import requests

from agents.normalizer_agent import normalize_capabilities
from agents.retrieval_agent import embed_batch
from agents.validator_agent import ValidatorAgent
from db.database import (
    get_db,
    upsert_facility,
    upsert_capabilities,
    upsert_equipment,
    upsert_chunk,
    update_job,
    execute,
)


DEFAULT_SHEET_URL = os.getenv(
    "GOOGLE_SHEET_URL",
    "https://docs.google.com/spreadsheets/d/1ZDuDmoQlyxZIEahDBlrMjf2wiWG7xU81/edit?gid=1028775758#gid=1028775758",
)
DEFAULT_GID = os.getenv("GOOGLE_SHEET_GID", "1028775758")


def _http_session() -> requests.Session:
    session = requests.Session()
    session.trust_env = False
    return session


def to_csv_export_url(sheet_url: str, gid: str | None = None) -> str:
    """Convert a Google Sheet edit URL or sheet ID to CSV export URL."""
    if "/export?" in sheet_url and "format=csv" in sheet_url:
        return sheet_url

    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", sheet_url)
    if m:
        sheet_id = m.group(1)
    else:
        sheet_id = sheet_url.strip()

    gid_match = re.search(r"[?&#]gid=(\d+)", sheet_url)
    resolved_gid = gid or (gid_match.group(1) if gid_match else DEFAULT_GID)
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={resolved_gid}"


def _parse_listish(value: Any) -> list[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]

    s = str(value).strip()
    if not s or s.lower() == "nan":
        return []

    # JSON array path
    try:
        loaded = json.loads(s)
        if isinstance(loaded, list):
            return [str(v).strip() for v in loaded if str(v).strip()]
    except Exception:
        pass

    # fallback: split comma-delimited
    return [p.strip() for p in s.split(",") if p.strip()]


def _normalize_scalar(value: Any) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    s = str(value).strip()
    return s if s and s.lower() not in {"nan", "null", "none"} else None


def _safe_str(row: pd.Series, key: str) -> str | None:
    return _normalize_scalar(row.get(key))


def _safe_float(row: pd.Series, key: str) -> float | None:
    val = _normalize_scalar(row.get(key))
    if val is None:
        return None
    try:
        return float(val)
    except Exception:
        return None


def _safe_int(row: pd.Series, key: str) -> int | None:
    val = _normalize_scalar(row.get(key))
    if val is None:
        return None
    try:
        return int(float(val))
    except Exception:
        return None


def _normalize_url(value: str | None) -> str | None:
    if not value:
        return None
    if re.match(r"^https?://", value, re.IGNORECASE):
        return value
    if re.match(r"^[\w.-]+\.[a-z]{2,}([/?#].*)?$", value, re.IGNORECASE):
        return f"https://{value}"
    return value


def _load_sheet_dataframe(sheet_url: str, gid: str | None = None) -> tuple[str, pd.DataFrame]:
    csv_url = to_csv_export_url(sheet_url, gid)
    response = _http_session().get(
        csv_url,
        timeout=30,
        headers={"User-Agent": "MediFind/1.0 (+https://vercel.com)"},
    )
    response.raise_for_status()

    body = response.text.lstrip("\ufeff")
    if "<html" in body[:300].lower():
        raise ValueError(
            "Google Sheet export returned HTML instead of CSV. Share the sheet/tab with "
            "'Anyone with the link' or use a direct CSV export URL."
        )

    df = pd.read_csv(StringIO(body), dtype=str, keep_default_na=False)
    df.columns = [str(col).strip() for col in df.columns]
    df = df.dropna(axis=0, how="all").dropna(axis=1, how="all")
    return csv_url, df


def _build_facility_id(row: pd.Series) -> str:
    phone_numbers = _parse_listish(row.get("phone_numbers"))
    key_parts = [
        (_safe_str(row, "name") or "").lower(),
        (_safe_str(row, "address_city") or "").lower(),
        (_safe_str(row, "address_stateOrRegion") or "").lower(),
        (_safe_str(row, "officialPhone") or (phone_numbers[0] if phone_numbers else "")).lower(),
        (_normalize_url(_safe_str(row, "officialWebsite")) or "").lower(),
    ]
    fingerprint = "|".join(key_parts).strip("|")
    if not fingerprint:
        fingerprint = str(uuid.uuid4())
    digest = hashlib.sha1(fingerprint.encode("utf-8")).hexdigest()
    return str(uuid.uuid5(uuid.NAMESPACE_URL, digest))


def count_rows(sheet_url: str = DEFAULT_SHEET_URL, gid: str = DEFAULT_GID, limit: int | None = None) -> int:
    _, df = _load_sheet_dataframe(sheet_url, gid)
    if limit:
        return min(limit, len(df))
    return len(df)


def ingest_google_sheet(
    sheet_url: str = DEFAULT_SHEET_URL,
    gid: str = DEFAULT_GID,
    limit: int | None = None,
    job_id: str | None = None,
) -> dict:
    """Ingest facilities directly from Google Sheet CSV export URL."""
    csv_url, df = _load_sheet_dataframe(sheet_url, gid)
    if limit:
        df = df.head(limit)

    validator = ValidatorAgent()
    processed = 0
    failed = 0
    row_errors: list[str] = []

    try:
        with get_db() as conn:
        # Ensure provenance table exists even if schema migration lagged
            execute(conn, """
                CREATE TABLE IF NOT EXISTS ingestion_sources (
                    id SERIAL PRIMARY KEY,
                    job_id UUID,
                    source_type TEXT NOT NULL,
                    source_url TEXT,
                    gid TEXT,
                    csv_url TEXT,
                    rows_fetched INTEGER DEFAULT 0,
                    rows_inserted INTEGER DEFAULT 0,
                    rows_failed INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'RUNNING',
                    message TEXT,
                    started_at TIMESTAMPTZ DEFAULT NOW(),
                    completed_at TIMESTAMPTZ
                )
            """)

            execute(conn, """
                INSERT INTO ingestion_sources (job_id, source_type, source_url, gid, csv_url, rows_fetched, status)
                VALUES (%s, 'google_sheet', %s, %s, %s, %s, 'RUNNING')
            """, (job_id, sheet_url, gid, csv_url, len(df)))

            if job_id:
                execute(conn, "UPDATE ingestion_jobs SET total_files = %s WHERE job_id = %s", (len(df), job_id))

            for _, row in df.iterrows():
                name = _safe_str(row, "name")
                if not name:
                    failed += 1
                    continue

                specialties = _parse_listish(row.get("specialties"))
                procedures = _parse_listish(row.get("procedure"))
                equipment = _parse_listish(row.get("equipment"))
                raw_capability = _parse_listish(row.get("capability"))
                phone_numbers = _parse_listish(row.get("phone_numbers"))
                websites = [_normalize_url(url) for url in _parse_listish(row.get("websites"))]
                websites = [url for url in websites if url]
                description = _safe_str(row, "description") or ""

                combined = specialties + procedures + equipment + raw_capability + ([description] if description else [])
                normalized_caps = normalize_capabilities(combined)
                cap_ids = [c["capability_id"] for c in normalized_caps]

                emergency_tokens = " ".join(combined).lower()
                emergency_24x7 = any(tok in emergency_tokens for tok in ["24x7", "24/7", "emergency", "trauma"])

                facility_data = {
                    "facility_id": _build_facility_id(row),
                    "facility_name": name,
                    "facility_name_normalized": name.lower().strip(),
                    "facility_type": (_safe_str(row, "facilityTypeId") or "clinic").replace("_", " ").title(),
                    "address": " ".join(filter(None, [_safe_str(row, "address_line1"), _safe_str(row, "address_line2"), _safe_str(row, "address_line3")])),
                    "pin_code": _safe_str(row, "address_zipOrPostcode"),
                    "state": _safe_str(row, "address_stateOrRegion"),
                    "district": _safe_str(row, "address_city") or _safe_str(row, "address_stateOrRegion"),
                    "city": _safe_str(row, "address_city"),
                    "lat": _safe_float(row, "latitude"),
                    "lng": _safe_float(row, "longitude"),
                    "geocoded": _safe_float(row, "latitude") is not None and _safe_float(row, "longitude") is not None,
                    "contact_phone": _safe_str(row, "officialPhone") or (phone_numbers[0] if phone_numbers else None),
                    "contact_email": _safe_str(row, "email"),
                    "website": _normalize_url(_safe_str(row, "officialWebsite")) or (websites[0] if websites else None),
                    "emergency_24x7": emergency_24x7,
                    "total_beds": _safe_int(row, "capacity") or 0,
                    "icu_beds": 0,
                    "nicu_beds": 0,
                    "accreditations": [],
                    "operational_hours": "24x7" if emergency_24x7 else None,
                    "source_doc_id": None,
                    "source_excerpt": description[:500] if description else "Imported from Google Sheet",
                    "extraction_confidence": 0.82,
                    "trust_score": 1.0,
                    "trust_flags": [],
                    "data_age_days": 180,
                }

                try:
                    facility_data = validator.run(facility_data)
                    fac_id = upsert_facility(conn, facility_data)
                    upsert_capabilities(conn, fac_id, normalized_caps)
                    upsert_equipment(conn, fac_id, equipment)

                    chunk_text = " | ".join([
                        name,
                        facility_data.get("city") or "",
                        description,
                        ", ".join(specialties[:20]),
                        ", ".join(procedures[:20]),
                        ", ".join(raw_capability[:20]),
                    ]).strip()
                    if not chunk_text:
                        chunk_text = f"{name} healthcare facility"

                    embedding = embed_batch([chunk_text])[0]
                    upsert_chunk(conn, {
                        "chunk_id": str(uuid.uuid4()),
                        "doc_id": None,
                        "facility_id": fac_id,
                        "chunk_text": chunk_text[:8000],
                        "chunk_index": 0,
                        "page_number": 1,
                        "token_count": len(chunk_text.split()),
                        "embedding": embedding,
                        "facility_name": facility_data.get("facility_name"),
                        "state": facility_data.get("state"),
                        "district": facility_data.get("district"),
                        "facility_type": facility_data.get("facility_type"),
                        "emergency_24x7": facility_data.get("emergency_24x7"),
                        "capabilities": cap_ids,
                    })
                    processed += 1
                except Exception as row_error:
                    failed += 1
                    if len(row_errors) < 10:
                        row_errors.append(f"{name}: {row_error}")

                if job_id:
                    update_job(conn, job_id, processed + failed, failed, "RUNNING")
                    execute(conn, """
                        UPDATE ingestion_sources
                        SET rows_inserted = %s, rows_failed = %s
                        WHERE job_id = %s AND source_type = 'google_sheet'
                    """, (processed, failed, job_id))

            if job_id:
                update_job(conn, job_id, processed + failed, failed, "COMPLETE")
                message = f"Imported {processed} rows from Google Sheet"
                if row_errors:
                    message = f"{message}. Sample failures: {' | '.join(row_errors[:3])}"
                execute(conn, """
                    UPDATE ingestion_sources
                    SET rows_inserted = %s,
                        rows_failed = %s,
                        status = 'COMPLETE',
                        completed_at = NOW(),
                        message = %s
                    WHERE job_id = %s AND source_type = 'google_sheet'
                """, (processed, failed, message, job_id))
    except Exception as e:
        with get_db() as conn:
            if job_id:
                update_job(conn, job_id, processed + failed, failed, "FAILED")
                execute(conn, """
                    UPDATE ingestion_sources
                    SET rows_inserted = %s,
                        rows_failed = %s,
                        status = 'FAILED',
                        completed_at = NOW(),
                        message = %s
                    WHERE job_id = %s AND source_type = 'google_sheet'
                """, (processed, failed, f'Ingestion failed: {e}', job_id))
        raise

    return {
        "total": len(df),
        "completed": processed,
        "failed": failed,
        "csv_url": csv_url,
        "errors": row_errors,
    }
