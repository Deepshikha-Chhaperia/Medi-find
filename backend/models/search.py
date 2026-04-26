"""Pydantic models for Search request/response."""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


class LocationIn(BaseModel):
    lat: float
    lng: float


class SearchFilters(BaseModel):
    facility_type: Optional[str] = None
    emergency_only: bool = False
    min_confidence: float = 0.0


class SearchRequest(BaseModel):
    query: str
    location: Optional[LocationIn] = None
    radius_km: float = 50.0
    filters: SearchFilters = Field(default_factory=SearchFilters)
    max_results: int = 10
    sort_by: str = "match"  # match | distance | beds | capabilities


class FacilityResult(BaseModel):
    rank: int
    facility_id: str
    facility_name: str
    facility_type: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    distance_km: float = 0.0
    match_score: float
    match_confidence: str  # High | Medium | Low
    matched_capabilities: list[str] = Field(default_factory=list)
    matched_reason: str = ""
    source_excerpt: Optional[str] = None
    source_doc: Optional[str] = None
    contact_phone: Optional[str] = None
    emergency_24x7: bool = False
    total_beds: int = 0
    icu_beds: int = 0
    accreditations: list[str] = Field(default_factory=list)
    directions_url: str = ""
    data_age_days: int = 0
    capabilities: list[str] = Field(default_factory=list)
    equipment: list[str] = Field(default_factory=list)
    trust_score: float = 1.0
    trust_flags: list[str] = Field(default_factory=list)


class SearchResponse(BaseModel):
    query_id: str
    processing_time_ms: int
    total_found: int
    interpreted_need: str = ""
    results: list[FacilityResult]
    gaps: list[str] = Field(default_factory=list)
    trace: dict = Field(default_factory=dict)
    disclaimer: str = "Always call ahead to confirm current availability before traveling."
