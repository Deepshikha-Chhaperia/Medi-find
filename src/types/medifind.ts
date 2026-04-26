export type Capability =
  | "trauma_center" | "stroke_unit" | "cardiac_emergency" | "poison_control"
  | "icu_general" | "icu_cardiac" | "icu_neuro" | "nicu" | "picu"
  | "mri" | "ct_scan" | "pet_ct" | "cath_lab" | "pathology_lab"
  | "robotic_surgery" | "cardiac_surgery" | "neurosurgery"
  | "transplant_kidney" | "transplant_liver" | "bariatric_surgery"
  | "high_risk_pregnancy" | "c_section_24x7"
  | "radiation_therapy" | "chemotherapy" | "surgical_oncology"
  | "dialysis" | "blood_bank" | "burn_unit" | "psychiatric_unit";

export type FacilityType =
  | "Multi-specialty Hospital"
  | "Specialty Hospital"
  | "Primary Health Centre"
  | "Community Health Centre"
  | "Nursing Home"
  | "Clinic"
  | "Diagnostic Centre"
  | "Government Hospital";

export interface Facility {
  facility_id: string;
  facility_name: string;
  facility_type?: string;
  address?: string;
  pin_code?: string;
  state?: string;
  district?: string;
  city?: string;
  lat?: number;
  lng?: number;
  contact_phone?: string;
  contact_email?: string;
  website?: string;
  emergency_24x7: boolean;
  total_beds: number;
  icu_beds: number;
  nicu_beds?: number;
  capabilities: string[];
  equipment: string[];
  accreditations: string[];
  operational_hours?: string;
  source_doc?: string;
  source_excerpt?: string;
  extraction_confidence: number;
  trust_score: number;
  trust_flags: string[];
  data_age_days: number;
}

export interface SearchResult extends Facility {
  rank: number;
  distance_km: number;
  match_score: number;
  match_confidence: "High" | "Medium" | "Low";
  matched_capabilities: string[];
  matched_reason: string;
  directions_url: string;
}

export interface SearchResponse {
  query_id: string;
  processing_time_ms: number;
  total_found: number;
  interpreted_need: string;
  results: SearchResult[];
  gaps: string[];
  trace?: Record<string, any>;
  disclaimer: string;
}

export interface CapabilityMeta {
  id: Capability;
  label: string;
  category: string;
  aliases: string[];
  icon?: string;
}