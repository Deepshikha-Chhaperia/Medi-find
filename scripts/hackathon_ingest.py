"""
Hackathon dataset ingestor.
Ingests facility rows directly from the Google Sheet URL into PostgreSQL/pgvector.

Usage:
  python scripts/hackathon_ingest.py
  python scripts/hackathon_ingest.py --limit 500
  python scripts/hackathon_ingest.py --sheet-url "<google-sheet-url>" --gid 1028775758
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from pipeline.google_sheet_ingestion import ingest_google_sheet, DEFAULT_SHEET_URL, DEFAULT_GID


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest hackathon Google Sheet into MediFind DB")
    parser.add_argument("--limit", type=int, default=None, help="Process only first N rows")
    parser.add_argument("--sheet-url", type=str, default=DEFAULT_SHEET_URL, help="Google Sheet edit/export URL or sheet ID")
    parser.add_argument("--gid", type=str, default=DEFAULT_GID, help="Google Sheet tab gid")
    args = parser.parse_args()

    result = ingest_google_sheet(sheet_url=args.sheet_url, gid=args.gid, limit=args.limit)
    print("Ingestion complete")
    print(result)


if __name__ == "__main__":
    main()
