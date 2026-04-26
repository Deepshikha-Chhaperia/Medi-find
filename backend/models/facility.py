"""Pydantic models for Facility entities."""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field
import uuid


class FacilityBase(BaseModel):
    facility_name: str
    facility_type: Optional[str] = None
    address: Optional[str] = None
    pin_code: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    website: Optional[str] = None
    emergency_24x7: Optional[bool] = None
    total_beds: Optional[int] = None
    icu_beds: Optional[int] = None
    nicu_beds: Optional[int] = None
    accreditations: list[str] = Field(default_factory=list)
    operational_hours: Optional[str] = None
    extraction_confidence: float = 0.0
    trust_score: float = 1.0
    trust_flags: list[str] = Field(default_factory=list)
    data_age_days: int = 0
    source_excerpt: Optional[str] = None


class FacilityCreate(FacilityBase):
    source_doc_id: Optional[str] = None


class FacilityOut(FacilityBase):
    facility_id: str
    capabilities: list[str] = Field(default_factory=list)
    equipment: list[str] = Field(default_factory=list)
    source_doc: Optional[str] = None

    class Config:
        from_attributes = True


class CapabilityItem(BaseModel):
    capability_id: str
    capability_name: str
    raw_extracted_text: Optional[str] = None
    confidence: float = 0.5
