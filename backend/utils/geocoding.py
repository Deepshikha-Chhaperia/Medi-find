"""
Nominatim geocoding with PostgreSQL caching.
Rate-limited to 1 request/second per OSM ToS.
"""
from __future__ import annotations

import time
import hashlib
import requests
from typing import Optional, Tuple

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
HEADERS = {"User-Agent": "MediFind/1.0 (hackathon, non-commercial)"}
_LAST_CALL = 0.0


def _rate_limit() -> None:
    global _LAST_CALL
    elapsed = time.time() - _LAST_CALL
    if elapsed < 1.1:
        time.sleep(1.1 - elapsed)
    _LAST_CALL = time.time()


def geocode_address(address: str, conn=None) -> Tuple[Optional[float], Optional[float]]:
    """
    Forward geocode an address string.
    Uses PostgreSQL cache if conn provided.
    Returns (lat, lng) or (None, None) on failure.
    """
    key = hashlib.md5(address.lower().strip().encode()).hexdigest()

    # Check cache
    if conn:
        from db.database import get_cached_geocode, cache_geocode
        cached = get_cached_geocode(conn, key)
        if cached:
            return cached

    _rate_limit()
    try:
        resp = requests.get(
            NOMINATIM_URL,
            params={"q": address + ", India", "format": "json", "limit": 1},
            headers=HEADERS,
            timeout=10,
        )
        data = resp.json()
        if data:
            lat, lng = float(data[0]["lat"]), float(data[0]["lon"])
            if conn:
                from db.database import cache_geocode
                cache_geocode(conn, key, lat, lng)
            return lat, lng
    except Exception as e:
        print(f"[Geocode] Failed for '{address}': {e}")
    return None, None


def reverse_geocode(lat: float, lng: float) -> dict:
    """
    Reverse geocode coordinates to address components.
    Returns dict with city, district, state keys.
    """
    _rate_limit()
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lng, "format": "json", "zoom": 10},
            headers=HEADERS,
            timeout=10,
        )
        data = resp.json()
        addr = data.get("address", {})
        return {
            "city": addr.get("city") or addr.get("town") or addr.get("village") or "",
            "district": addr.get("county") or addr.get("state_district") or "",
            "state": addr.get("state") or "",
            "display": data.get("display_name", ""),
        }
    except Exception as e:
        print(f"[Geocode] Reverse failed for ({lat},{lng}): {e}")
        return {"city": "", "district": "", "state": "", "display": ""}
