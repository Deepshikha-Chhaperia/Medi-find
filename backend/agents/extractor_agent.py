"""
Agent 3: Entity Extractor
Uses Groq LLaMA 3.3-70B to extract structured facility data from raw document text.
"""
from __future__ import annotations
import uuid
from utils.groq_client import call_groq_json
from utils.text_utils import truncate_for_llm

EXTRACTION_PROMPT = """You are a healthcare data extraction specialist. Extract structured information from this hospital/clinic facility report text.

Return ONLY valid JSON with this exact structure (use null for missing fields):
{{
  "facility_name": "string or null",
  "facility_type": "one of [Multi-specialty Hospital, Specialty Hospital, Primary Health Centre, Community Health Centre, Nursing Home, Clinic, Diagnostic Centre, Government Hospital] or null",
  "address": "full address string or null",
  "pin_code": "6-digit code or null",
  "state": "Indian state name or null",
  "district": "district name or null",
  "city": "city name or null",
  "contact_phone": "phone number or null",
  "contact_email": "email or null",
  "website": "URL or null",
  "emergency_24x7": true/false/null,
  "total_beds": integer or null,
  "icu_beds": integer or null,
  "nicu_beds": integer or null,
  "specialties": ["list of specialties mentioned"],
  "departments": ["list of departments mentioned"],
  "equipment": ["list of medical equipment mentioned, include brand names"],
  "accreditations": ["NABH", "JCI", "NABL", "ISO", etc if mentioned],
  "operational_hours": "hours description or null",
  "extraction_confidence": 0.0-1.0
}}

Rules:
- Extract ONLY what is explicitly stated. Do NOT infer.
- If text is very short or unclear, set extraction_confidence below 0.5
- Include brand names in equipment (e.g., "3T Siemens MRI" not just "MRI")

TEXT:
{text}"""


def extract_entities(doc: dict) -> dict:
    """
    Run LLM extraction on a parsed document.
    Returns structured facility dict. Returns partial dict if LLM fails.
    """
    raw_text = doc.get("raw_text", "")
    if not raw_text.strip():
        return {}

    truncated = truncate_for_llm(raw_text, max_tokens=3000)
    result = call_groq_json(EXTRACTION_PROMPT.format(text=truncated))

    if not result:
        return {"extraction_confidence": 0.0}

    # Normalise
    return {
        "facility_id": str(uuid.uuid4()),
        "facility_name": result.get("facility_name") or "Unknown Facility",
        "facility_name_normalized": (result.get("facility_name") or "").lower().strip(),
        "facility_type": result.get("facility_type"),
        "address": result.get("address"),
        "pin_code": result.get("pin_code"),
        "state": result.get("state"),
        "district": result.get("district"),
        "city": result.get("city"),
        "contact_phone": result.get("contact_phone"),
        "contact_email": result.get("contact_email"),
        "website": result.get("website"),
        "emergency_24x7": result.get("emergency_24x7"),
        "total_beds": result.get("total_beds"),
        "icu_beds": result.get("icu_beds"),
        "nicu_beds": result.get("nicu_beds"),
        "accreditations": result.get("accreditations", []),
        "operational_hours": result.get("operational_hours"),
        "extraction_confidence": float(result.get("extraction_confidence", 0.5)),
        "source_doc_id": doc.get("doc_id"),
        # Raw lists for normalizer
        "_raw_specialties": result.get("specialties", []),
        "_raw_departments": result.get("departments", []),
        "_raw_equipment": result.get("equipment", []),
    }
