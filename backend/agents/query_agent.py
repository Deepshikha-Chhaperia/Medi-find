"""
Agent 5: Query Decomposer
Converts natural language user queries into structured retrieval parameters via Groq.
"""
from __future__ import annotations
from utils.groq_client import call_groq_json

DECOMPOSE_PROMPT = """You are a healthcare search assistant. Convert the user's natural language query into structured search parameters.

User query: "{query}"
User location: lat={lat}, lng={lng}

Return ONLY valid JSON:
{{
  "interpreted_need": "one sentence plain-English summary of what the user needs",
  "urgency": "emergency|urgent|routine",
  "location_description": "city/area extracted from query, or null",
  "radius_km": 10,
  "required_capabilities": ["list of canonical IDs from: trauma_center, stroke_unit, cardiac_emergency, poison_control, icu_general, icu_cardiac, icu_neuro, nicu, picu, mri, ct_scan, pet_ct, cath_lab, pathology_lab, robotic_surgery, cardiac_surgery, neurosurgery, transplant_kidney, transplant_liver, bariatric_surgery, high_risk_pregnancy, c_section_24x7, radiation_therapy, chemotherapy, surgical_oncology, dialysis, blood_bank, burn_unit, psychiatric_unit"],
  "must_be_24x7": true/false,
  "preferred_facility_type": "facility type or null",
  "sub_queries": [
    "rephrasing 1 for semantic search",
    "rephrasing 2 with medical terminology",
    "rephrasing 3 with alternate phrasing"
  ],
  "search_keywords": ["key medical terms"]
}}

Rules:
- radius_km: emergency=10, urgent=20, routine=50
- must_be_24x7: true if query mentions emergency/urgent/24 hours/night
- Include at least 3 sub_queries that rephrase the query differently"""


def decompose_query(query: str, lat: float | None = None, lng: float | None = None) -> dict:
    """
    Break a natural language query into structured retrieval instructions.
    Returns dict with required_capabilities, sub_queries, etc.
    """
    prompt = DECOMPOSE_PROMPT.format(
        query=query,
        lat=lat or "unknown",
        lng=lng or "unknown",
    )
    result = call_groq_json(prompt, max_tokens=800)
    if not result:
        # Fallback: minimal structure
        return {
            "interpreted_need": query,
            "urgency": "routine",
            "location_description": None,
            "radius_km": 50,
            "required_capabilities": [],
            "must_be_24x7": False,
            "sub_queries": [query],
            "search_keywords": query.split(),
        }
    return result
