from __future__ import annotations

import json
import os
import re
import uuid
from io import StringIO
from typing import Any

import pandas as pd
import requests

from agents.normalizer_agent import normalize_capabilities

DEFAULT_SHEET_URL = os.getenv(
    "GOOGLE_SHEET_URL",
    "https://docs.google.com/spreadsheets/d/1ZDuDmoQlyxZIEahDBlrMjf2wiWG7xU81/edit?gid=1028775758#gid=1028775758",
)
DEFAULT_GID = os.getenv("GOOGLE_SHEET_GID", "1028775758")


def _http_session() -> requests.Session:
    session = requests.Session()
    # Some local/dev environments inject broken proxy settings into requests.
    # Google Sheets export works correctly when we bypass those inherited proxies.
    session.trust_env = False
    return session


def to_csv_export_url(sheet_url: str, gid: str | None = None) -> str:
    if "/export?" in sheet_url and "format=csv" in sheet_url:
        return sheet_url

    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", sheet_url)
    sheet_id = match.group(1) if match else sheet_url.strip()
    gid_match = re.search(r"[?&#]gid=(\d+)", sheet_url)
    resolved_gid = gid or (gid_match.group(1) if gid_match else DEFAULT_GID)
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={resolved_gid}"


def _normalize_scalar(value: Any) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    return text if text and text.lower() not in {"nan", "null", "none"} else None


def _parse_listish(value: Any) -> list[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]

    text = str(value).strip()
    if not text or text.lower() in {"nan", "null", "none"}:
        return []

    try:
        loaded = json.loads(text)
        if isinstance(loaded, list):
            return [str(v).strip() for v in loaded if str(v).strip()]
    except Exception:
        pass

    return [part.strip() for part in text.split(",") if part.strip()]


def _normalize_url(value: str | None) -> str | None:
    if not value:
        return None
    if re.match(r"^https?://", value, re.IGNORECASE):
        return value
    if re.match(r"^[\w.-]+\.[a-z]{2,}([/?#].*)?$", value, re.IGNORECASE):
        return f"https://{value}"
    return value


def _safe_str(row: pd.Series, key: str) -> str | None:
    return _normalize_scalar(row.get(key))


def _safe_float(row: pd.Series, key: str) -> float | None:
    value = _normalize_scalar(row.get(key))
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def _safe_int(row: pd.Series, key: str) -> int | None:
    value = _normalize_scalar(row.get(key))
    if value is None:
        return None
    try:
        return int(float(value))
    except Exception:
        return None


def load_sheet_dataframe(sheet_url: str = DEFAULT_SHEET_URL, gid: str = DEFAULT_GID) -> tuple[str, pd.DataFrame]:
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


def _row_to_facility(row: pd.Series) -> dict | None:
    name = _safe_str(row, "name")
    if not name:
        return None

    specialties = _parse_listish(row.get("specialties"))
    procedures = _parse_listish(row.get("procedure"))
    equipment = _parse_listish(row.get("equipment"))
    raw_capability = _parse_listish(row.get("capability"))
    phone_numbers = _parse_listish(row.get("phone_numbers"))
    description = _safe_str(row, "description") or ""
    combined_terms = specialties + procedures + equipment + raw_capability + ([description] if description else [])
    normalized_caps = normalize_capabilities(combined_terms)

    emergency_tokens = " ".join(combined_terms).lower()
    emergency_24x7 = any(tok in emergency_tokens for tok in ["24x7", "24/7", "emergency", "trauma"])

    address = " ".join(filter(None, [
        _safe_str(row, "address_line1"),
        _safe_str(row, "address_line2"),
        _safe_str(row, "address_line3"),
    ]))
    city = _safe_str(row, "address_city")
    state = _safe_str(row, "address_stateOrRegion")
    website = _normalize_url(_safe_str(row, "officialWebsite"))
    if not website:
        websites = [_normalize_url(url) for url in _parse_listish(row.get("websites"))]
        website = next((url for url in websites if url), None)

    stable_key = "|".join(filter(None, [
        name.lower(),
        (city or "").lower(),
        (state or "").lower(),
        (_safe_str(row, "officialPhone") or (phone_numbers[0] if phone_numbers else "")).lower(),
        (website or "").lower(),
    ]))

    return {
        "facility_id": str(uuid.uuid5(uuid.NAMESPACE_URL, stable_key or name.lower())),
        "facility_name": name,
        "facility_type": (_safe_str(row, "facilityTypeId") or "clinic").replace("_", " ").title(),
        "address": address,
        "pin_code": _safe_str(row, "address_zipOrPostcode"),
        "state": state,
        "district": city or state,
        "city": city,
        "lat": _safe_float(row, "latitude") or 0.0,
        "lng": _safe_float(row, "longitude") or 0.0,
        "contact_phone": _safe_str(row, "officialPhone") or (phone_numbers[0] if phone_numbers else None),
        "contact_email": _safe_str(row, "email"),
        "website": website,
        "emergency_24x7": emergency_24x7,
        "total_beds": _safe_int(row, "capacity") or 0,
        "icu_beds": 0,
        "nicu_beds": 0,
        "capabilities": [cap["capability_id"] for cap in normalized_caps],
        "equipment": equipment,
        "accreditations": [],
        "operational_hours": "24x7" if emergency_24x7 else None,
        "source_doc": "Google Sheet",
        "source_excerpt": description or "Imported from Google Sheet",
        "extraction_confidence": 0.82,
        "trust_score": 1.0,
        "trust_flags": [],
        "data_age_days": 180,
        "raw_specialties": specialties,
        "raw_procedures": procedures,
        "raw_capability": raw_capability,
    }


def load_public_facilities(
    sheet_url: str = DEFAULT_SHEET_URL,
    gid: str = DEFAULT_GID,
    limit: int | None = None,
) -> dict:
    csv_url, df = load_sheet_dataframe(sheet_url, gid)
    if limit:
        df = df.head(limit)

    facilities = []
    for _, row in df.iterrows():
        facility = _row_to_facility(row)
        if facility:
            facilities.append(facility)

    return {
        "sheet_url": sheet_url,
        "gid": gid,
        "csv_url": csv_url,
        "total_rows": len(df),
        "facilities": facilities,
    }
