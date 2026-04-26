"""
POST /api/ingest — file upload and pipeline trigger.
GET /api/ingest/status/:job_id — job progress.
"""
import os
import uuid
import threading
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from db.database import get_db, create_job, fetchone
from db.database import update_job, execute
from pipeline.ingestion import ingest_directory
from pipeline.google_sheet_ingestion import (
    DEFAULT_GID,
    DEFAULT_SHEET_URL,
    ingest_google_sheet,
    count_rows,
)

DATA_DIR = os.getenv("DATA_DIR", "./data/raw")
router = APIRouter(prefix="/api/ingest", tags=["ingest"])

# In-memory job state (augmented by DB)
_active_jobs: dict[str, dict] = {}


def _should_run_inline() -> bool:
    forced = os.getenv("INGEST_INLINE")
    if forced is not None:
        return forced.lower() == "true"
    return any(
        os.getenv(flag)
        for flag in ("VERCEL", "NOW_REGION", "AWS_LAMBDA_FUNCTION_NAME")
    )


@router.post("")
async def ingest_files(files: list[UploadFile] = File(...)):
    """
    Accept one or more facility report files, save them, and start ingestion pipeline.
    Returns job_id for polling.
    """
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)

    saved_paths = []
    for f in files:
        safe_name = Path(f.filename).name if f.filename else f"upload_{uuid.uuid4()}.txt"
        dest = Path(DATA_DIR) / safe_name
        content = await f.read()
        with open(dest, "wb") as out:
            out.write(content)
        saved_paths.append(str(dest))

    # Create job in DB
    with get_db() as conn:
        job_id = create_job(conn, len(saved_paths))

    # Run ingestion in a background thread (non-blocking API response)
    def _run():
        ingest_directory(DATA_DIR, job_id=job_id)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    _active_jobs[job_id] = {"thread": thread}

    return {"job_id": job_id, "total_files": len(saved_paths), "status": "RUNNING"}


@router.get("/status/{job_id}")
def job_status(job_id: str):
    """Poll ingestion job progress."""
    with get_db() as conn:
        job = fetchone(conn, "SELECT * FROM ingestion_jobs WHERE job_id = %s", (job_id,))
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": job_id,
        "status": job["status"],
        "total_files": job["total_files"],
        "processed_files": job["processed_files"],
        "failed_files": job["failed_files"],
        "pct_complete": round(
            (job["processed_files"] / max(1, job["total_files"])) * 100, 1
        ),
    }


@router.get("/jobs")
def list_jobs():
    """List all ingestion jobs."""
    with get_db() as conn:
        from db.database import fetchall
        jobs = fetchall(conn,
            "SELECT job_id, status, total_files, processed_files, failed_files, started_at FROM ingestion_jobs ORDER BY started_at DESC LIMIT 20")
    return jobs


@router.get("/source-status")
def source_status(limit: int = 10):
    """Latest ingestion source provenance records."""
    with get_db() as conn:
        from db.database import fetchall
        rows = fetchall(conn, """
            SELECT id, job_id, source_type, source_url, gid, csv_url,
                   rows_fetched, rows_inserted, rows_failed, status,
                   message, started_at, completed_at
            FROM ingestion_sources
            ORDER BY started_at DESC
            LIMIT %s
        """, (limit,))
    return {"sources": rows}


@router.get("/source-status/{job_id}")
def source_status_by_job(job_id: str):
    """Provenance record for a specific job id."""
    with get_db() as conn:
        from db.database import fetchone
        row = fetchone(conn, """
            SELECT id, job_id, source_type, source_url, gid, csv_url,
                   rows_fetched, rows_inserted, rows_failed, status,
                   message, started_at, completed_at
            FROM ingestion_sources
            WHERE job_id = %s
            ORDER BY started_at DESC
            LIMIT 1
        """, (job_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Source provenance not found for this job")
    return row


@router.post("/google-sheet")
def ingest_google_sheet_endpoint(
    sheet_url: str = DEFAULT_SHEET_URL,
    gid: str = DEFAULT_GID,
    limit: Optional[int] = None,
):
    """Trigger ingestion directly from a Google Sheet URL (CSV export under the hood)."""
    try:
        total_files = count_rows(sheet_url=sheet_url, gid=gid, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Unable to read Google Sheet: {e}") from e

    with get_db() as conn:
        job_id = create_job(conn, total_files)

    if _should_run_inline():
        try:
            result = ingest_google_sheet(sheet_url=sheet_url, gid=gid, limit=limit, job_id=job_id)
            return {
                "job_id": job_id,
                "status": "COMPLETE",
                "source": "google_sheet",
                "sheet_url": sheet_url,
                "gid": gid,
                "total_rows": total_files,
                "completed_rows": result["completed"],
                "failed_rows": result["failed"],
                "csv_url": result["csv_url"],
                "errors": result.get("errors", []),
                "execution_mode": "inline",
            }
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Google Sheet ingestion failed for job {job_id}: {e}",
            ) from e

    def _run_google_sheet():
        try:
            ingest_google_sheet(sheet_url=sheet_url, gid=gid, limit=limit, job_id=job_id)
        except Exception as e:
            with get_db() as conn:
                update_job(conn, job_id, 0, 0, "FAILED")
                execute(conn, """
                    UPDATE ingestion_sources
                    SET status = 'FAILED',
                        message = %s,
                        completed_at = NOW()
                    WHERE job_id = %s AND source_type = 'google_sheet'
                """, (f"Google Sheet ingestion failed: {e}", job_id))

    thread = threading.Thread(target=_run_google_sheet, daemon=True)
    thread.start()
    _active_jobs[job_id] = {"thread": thread, "type": "google_sheet"}

    return {
        "job_id": job_id,
        "status": "RUNNING",
        "source": "google_sheet",
        "sheet_url": sheet_url,
        "gid": gid,
        "total_rows": total_files,
        "execution_mode": "background",
    }
