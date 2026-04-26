from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException

from utils.google_sheet_source import DEFAULT_GID, DEFAULT_SHEET_URL, load_public_facilities

router = APIRouter(prefix="/api/public", tags=["public"])


@router.get("/facilities")
def public_facilities(
    sheet_url: str = DEFAULT_SHEET_URL,
    gid: str = DEFAULT_GID,
    limit: Optional[int] = None,
):
    try:
        return load_public_facilities(sheet_url=sheet_url, gid=gid, limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Unable to load public facilities: {exc}") from exc
