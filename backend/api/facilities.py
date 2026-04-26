"""
GET /api/facilities — facility list and detail endpoints.
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from db.database import get_db, fetchone, fetchall
from models.facility import FacilityOut

router = APIRouter(prefix="/api/facilities", tags=["facilities"])


@router.get("/{facility_id}", response_model=FacilityOut)
def get_facility(facility_id: str):
    """Full facility intelligence card."""
    with get_db() as conn:
        fac = fetchone(conn, "SELECT * FROM facilities WHERE facility_id = %s", (facility_id,))
        if not fac:
            raise HTTPException(status_code=404, detail="Facility not found")
        caps = fetchall(conn,
            "SELECT capability_id FROM facility_capabilities WHERE facility_id = %s", (facility_id,))
        equip = fetchall(conn,
            "SELECT equipment_name FROM facility_equipment WHERE facility_id = %s", (facility_id,))
        source_doc = None
        if fac.get("source_doc_id"):
            doc = fetchone(conn, "SELECT source_file FROM documents WHERE doc_id = %s",
                           (fac["source_doc_id"],))
            source_doc = doc["source_file"] if doc else None

    return FacilityOut(
        **fac,
        capabilities=[c["capability_id"] for c in caps],
        equipment=[e["equipment_name"] for e in equip if e["equipment_name"]],
        source_doc=source_doc,
    )


@router.get("", response_model=list[FacilityOut])
def list_facilities(
    q: Optional[str] = Query(None, description="Text filter on facility name/city/address"),
    capability: Optional[str] = Query(None, description="Canonical capability_id filter"),
    state: Optional[str] = Query(None),
    district: Optional[str] = Query(None),
    facility_type: Optional[str] = Query(None),
    emergency_only: bool = Query(False),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
):
    """List facilities with optional filters."""
    filters, params = [], []
    if q:
        filters.append("(facility_name ILIKE %s OR city ILIKE %s OR address ILIKE %s)")
        like = f"%{q}%"
        params.extend([like, like, like])
    if state:
        filters.append("state = %s")
        params.append(state)
    if district:
        filters.append("district = %s")
        params.append(district)
    if facility_type:
        filters.append("facility_type = %s")
        params.append(facility_type)
    if emergency_only:
        filters.append("emergency_24x7 = TRUE")

    if capability:
        filters.append("facility_id IN (SELECT facility_id FROM facility_capabilities WHERE capability_id = %s)")
        params.append(capability)

    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    sql = f"SELECT * FROM facilities {where} ORDER BY facility_name LIMIT %s OFFSET %s"
    params += [limit, offset]

    with get_db() as conn:
        rows = fetchall(conn, sql, params)
        results = []
        for fac in rows:
            fid = str(fac["facility_id"])
            caps = fetchall(conn,
                "SELECT capability_id FROM facility_capabilities WHERE facility_id = %s", (fid,))
            results.append(FacilityOut(
                **fac,
                capabilities=[c["capability_id"] for c in caps],
                equipment=[],
            ))
    return results
