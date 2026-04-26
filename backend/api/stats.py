"""
GET /api/stats — system statistics.
GET /api/capabilities/gaps — per-district gap analysis.
"""
from fastapi import APIRouter
from db.database import get_db, fetchone, fetchall

router = APIRouter(prefix="/api", tags=["stats"])


@router.get("/stats")
def get_stats():
    """System health and coverage stats."""
    with get_db() as conn:
        total_docs = fetchone(conn, "SELECT COUNT(*) AS n FROM documents")
        total_facilities = fetchone(conn, "SELECT COUNT(*) AS n FROM facilities")
        avg_confidence = fetchone(conn,
            "SELECT AVG(extraction_confidence) AS v FROM facilities")
        total_caps = fetchone(conn, "SELECT COUNT(*) AS n FROM facility_capabilities")
        state_breakdown = fetchall(conn,
            "SELECT state, COUNT(*) AS count FROM facilities WHERE state IS NOT NULL GROUP BY state ORDER BY count DESC")
        recent_queries = fetchone(conn,
            "SELECT COUNT(*) AS n FROM search_queries WHERE created_at > NOW() - INTERVAL '24 hours'")

    return {
        "connected": True,
        "total_documents": total_docs["n"] if total_docs else 0,
        "total_facilities": total_facilities["n"] if total_facilities else 0,
        "total_capabilities_indexed": total_caps["n"] if total_caps else 0,
        "avg_extraction_confidence": round(float(avg_confidence["v"] or 0), 2),
        "queries_last_24h": recent_queries["n"] if recent_queries else 0,
        "state_breakdown": state_breakdown or [],
    }


@router.get("/capabilities/gaps")
def capability_gaps():
    """
    Returns per-district capability gap analysis:
    which capabilities are absent from any indexed facility in that district.
    """
    KNOWN_CAPS = [
        "trauma_center", "stroke_unit", "cardiac_emergency", "nicu", "picu",
        "icu_general", "icu_cardiac", "icu_neuro", "mri", "ct_scan", "pet_ct",
        "cath_lab", "robotic_surgery", "cardiac_surgery", "neurosurgery",
        "dialysis", "blood_bank", "burn_unit", "psychiatric_unit",
        "radiation_therapy", "chemotherapy",
    ]

    with get_db() as conn:
        districts = fetchall(conn,
            "SELECT DISTINCT district, state FROM facilities WHERE district IS NOT NULL")
        gaps = []
        for d in districts:
            dist_name = d["district"]
            state = d["state"]
            present = fetchall(conn, """
                SELECT DISTINCT fc.capability_id
                FROM facility_capabilities fc
                JOIN facilities f ON f.facility_id = fc.facility_id
                WHERE f.district = %s
            """, (dist_name,))
            present_ids = {r["capability_id"] for r in present}
            missing = [c for c in KNOWN_CAPS if c not in present_ids]
            if missing:
                gaps.append({"district": dist_name, "state": state, "missing": missing})

    return {"gaps": gaps}


@router.get("/capabilities")
def list_capabilities():
    """Return full capability taxonomy."""
    import json, os
    ont_path = os.path.join(os.path.dirname(__file__), "..", "data", "capability_ontology.json")
    with open(os.path.normpath(ont_path), "r") as f:
        return json.load(f)
