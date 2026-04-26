"""
Bulk ingest all files from backend/data/raw/ into the MediFind database.
Uses the full 8-agent pipeline per file.

Usage:
  python scripts/bulk_ingest.py [--limit N] [--dir PATH]

Options:
  --limit N    Process only the first N files (useful for testing)
  --dir PATH   Override the input directory
"""
import os
import sys
import argparse
from pathlib import Path
from tqdm import tqdm

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))

from db.database import init_db, get_db, create_job, update_job
from pipeline.ingestion import ingest_file

SUPPORTED_EXT = {".pdf", ".csv", ".xlsx", ".xls", ".docx", ".txt", ".html", ".htm"}

def main():
    parser = argparse.ArgumentParser(description="Bulk ingest facility reports into MediFind")
    parser.add_argument("--limit", type=int, default=None, help="Max files to process")
    parser.add_argument("--dir", type=str,
                        default=os.path.join(os.path.dirname(__file__), "..", "backend", "data", "raw"),
                        help="Directory with raw facility reports")
    args = parser.parse_args()

    raw_dir = Path(args.dir)
    if not raw_dir.exists():
        print(f"[Error] Directory not found: {raw_dir}")
        sys.exit(1)

    files = sorted([
        str(p) for p in raw_dir.iterdir()
        if p.suffix.lower() in SUPPORTED_EXT and p.is_file()
    ])

    if args.limit:
        files = files[:args.limit]

    if not files:
        print(f"[Warning] No supported files found in {raw_dir}")
        print("  Run: python scripts/generate_sample_data.py  first.")
        sys.exit(0)

    print(f"\n{'='*60}")
    print(f"  MediFind Bulk Ingest")
    print(f"  Files to process: {len(files)}")
    print(f"  Directory: {raw_dir}")
    print(f"{'='*60}\n")

    # Initialise DB schema
    init_db()

    # Create job record
    with get_db() as conn:
        job_id = create_job(conn, len(files))
    print(f"[Job] Started job: {job_id}\n")

    completed = 0
    failed = 0
    results_log = []

    with get_db() as conn:
        for fpath in tqdm(files, desc="Ingesting", unit="file"):
            result = ingest_file(fpath, job_id=job_id, conn=conn)
            if result.get("status") == "complete":
                completed += 1
                results_log.append(f"  ✓ {Path(fpath).name} → {result.get('facility_name', '?')}")
            else:
                failed += 1
                results_log.append(f"  ✗ {Path(fpath).name}: {result.get('error', '?')}")
            update_job(conn, job_id, completed + failed, failed,
                       "RUNNING" if (completed + failed) < len(files) else "COMPLETE")

    print(f"\n{'='*60}")
    print(f"  Ingestion Complete")
    print(f"  ✓ {completed} succeeded   ✗ {failed} failed")
    print(f"  Job ID: {job_id}")
    print(f"{'='*60}")
    for line in results_log:
        print(line)


if __name__ == "__main__":
    main()
