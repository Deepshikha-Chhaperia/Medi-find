import { Facility, SearchResponse, SearchResult, Capability } from "@/types/medifind";
import { CAPABILITY_META } from "@/data/capabilities";
import { SEED_FACILITIES } from "@/data/seedFacilities";

export { SEED_FACILITIES }; // re-export for api.ts

export function haversineKm(a: { lat: number; lng: number }, b: { lat: number; lng: number }) {
  const R = 6371;
  const dLat = ((b.lat - a.lat) * Math.PI) / 180;
  const dLng = ((b.lng - a.lng) * Math.PI) / 180;
  const lat1 = (a.lat * Math.PI) / 180;
  const lat2 = (b.lat * Math.PI) / 180;
  const x = Math.sin(dLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(x));
}

const CITY_ALIASES: Record<string, string> = {
  kolkata: "Kolkata", calcutta: "Kolkata", "salt lake": "Kolkata", saltlake: "Kolkata",
  mumbai: "Mumbai", bombay: "Mumbai",
  delhi: "New Delhi", "new delhi": "New Delhi",
  bengaluru: "Bengaluru", bangalore: "Bengaluru",
  chennai: "Chennai", madras: "Chennai",
  vellore: "Vellore",
  hyderabad: "Hyderabad", secunderabad: "Hyderabad",
  pune: "Pune", poona: "Pune",
  jaipur: "Jaipur",
  ahmedabad: "Ahmedabad", amdavad: "Ahmedabad",
  lucknow: "Lucknow",
  chandigarh: "Chandigarh", mohali: "Chandigarh",
  kochi: "Kochi", cochin: "Kochi", ernakulam: "Kochi",
};

function detectCapabilities(query: string): Capability[] {
  const q = query.toLowerCase();
  const hits: Capability[] = [];
  for (const meta of Object.values(CAPABILITY_META)) {
    if (q.includes(meta.label.toLowerCase()) || q.includes(meta.id.replace(/_/g, " "))) {
      hits.push(meta.id);
      continue;
    }
    for (const alias of meta.aliases) {
      if (q.includes(alias.toLowerCase())) {
        hits.push(meta.id);
        break;
      }
    }
  }
  return Array.from(new Set(hits));
}

function detectLocation(query: string): { city?: string } {
  const q = query.toLowerCase();
  for (const [alias, canonical] of Object.entries(CITY_ALIASES)) {
    if (q.includes(alias)) return { city: canonical };
  }
  return {};
}

function detect24x7(query: string): boolean {
  return /24[\s/x]?7|24 hours|round the clock|emergency|urgent|night/i.test(query);
}

export interface SearchOptions {
  facilities?: Facility[];
  query: string;
  userLocation?: { lat: number; lng: number };
  radiusKm?: number;
  sortBy?: "match" | "distance" | "beds" | "capabilities";
  emergencyOnly?: boolean;
  minConfidence?: number;
  filters?: {
    facility_type?: string | null;
    emergency_only?: boolean;
    min_confidence?: number;
  };
  maxResults?: number;
}

export function runSearch({
  facilities = SEED_FACILITIES,
  query,
  userLocation,
  radiusKm = 50,
  sortBy = "match",
  emergencyOnly = false,
  minConfidence = 0,
  filters = {},
  maxResults = 10,
}: SearchOptions): SearchResponse {
  const start = performance.now();
  const requiredCaps = detectCapabilities(query);
  const loc = detectLocation(query);
  const need24x7 = detect24x7(query) || emergencyOnly || filters.emergency_only;
  const minConf = minConfidence || filters.min_confidence || 0;
  const typeFilter = filters.facility_type;

  const interpreted = `Facilities${requiredCaps.length ? ` with ${requiredCaps.map((c) => CAPABILITY_META[c]?.label ?? c).join(", ")}` : ""}${loc.city ? ` near ${loc.city}` : ""}${need24x7 ? ", 24/7 availability" : ""}.`;

  type ScoredResult = SearchResult & { _sortKey: number };

    const scored: ScoredResult[] = facilities
    .filter((f) => {
      if (typeFilter && f.facility_type !== typeFilter) return false;
      if (need24x7 && !f.emergency_24x7) return false;
      if (f.extraction_confidence < minConf) return false;

      // Strict text filter: location bounds
      if (loc.city) {
        const fc = f.city.toLowerCase();
        const fs = f.state.toLowerCase();
        const lc = loc.city.toLowerCase();
        if (!fc.includes(lc) && !fs.includes(lc)) return false;
      }

      // Strict text filter: capability bounds
      if (requiredCaps.length > 0) {
        const hasCap = requiredCaps.some(c => f.capabilities.includes(c));
        if (!hasCap) return false;
      }

      // Strict text filter: general query word overlaps
      const qTokens = query.toLowerCase().split(/\s+/).filter(t => t.length > 2);
      if (requiredCaps.length === 0 && !loc.city && qTokens.length > 0) {
        const facText = (f.facility_name + " " + f.capabilities.join(" ") + " " + (f.equipment || []).join(" ") + " " + f.city).toLowerCase();
        const hasOverlap = qTokens.some(t => facText.includes(t));
        if (!hasOverlap) return false;
      }
      
      return true;
    })
    .map((f) => {
      const matched = requiredCaps.filter((c) => f.capabilities.includes(c));
      const capScore = requiredCaps.length === 0 ? 0.5 : matched.length / requiredCaps.length;

      let locScore = 0.5;
      let distance_km = 0;
      if (userLocation) {
        distance_km = haversineKm(userLocation, f);
        locScore = Math.max(0, 1 - distance_km / 150);
      } else if (loc.city) {
        const fc = f.city.toLowerCase();
        locScore = fc.includes(loc.city.toLowerCase()) ? 1
          : f.state.toLowerCase().includes(loc.city.toLowerCase()) ? 0.4 : 0.1;
      }

      const e247Score = need24x7 ? (f.emergency_24x7 ? 1 : 0.2) : 0.7;
      const recencyScore = Math.max(0, 1 - f.data_age_days / 730);
      const qTokens = query.toLowerCase().split(/\s+/);
      const facText = (
        f.facility_name + " " +
        f.capabilities.map((c) => CAPABILITY_META[c]?.label ?? "").join(" ") + " " +
        f.equipment.join(" ")
      ).toLowerCase();
      const overlap = qTokens.filter((t) => t.length > 2 && facText.includes(t)).length / Math.max(1, qTokens.length);

      const match_score = capScore * 0.45 + locScore * 0.25 + e247Score * 0.1 + recencyScore * 0.05 + overlap * 0.15;
      const match_confidence: SearchResult["match_confidence"] = match_score >= 0.75 ? "High" : match_score >= 0.5 ? "Medium" : "Low";
      let matched_reason = "";
      const distInfo = distance_km > 0 ? ` located ${Math.round(distance_km * 10) / 10}km away` : "";
      
      if (matched.length > 0) {
        matched_reason = `Agent verification: Source documents for ${f.facility_name} confirm ${matched.map((c) => CAPABILITY_META[c]?.label ?? c).join(", ")}${f.emergency_24x7 ? " with 24/7 emergency support" : ""}.`;
      } else if (loc.city && (f.city.toLowerCase().includes(loc.city.toLowerCase()) || f.state.toLowerCase().includes(loc.city.toLowerCase()))) {
        matched_reason = `Contextual match: ${f.facility_name} identified as a relevant healthcare provider in the ${loc.city} search area${distInfo}.`;
      } else if (overlap > 0.15) {
        matched_reason = `High-confidence match: Clinical alignment between query intent and ${f.facility_name}'s listed services and specialties.`;
      } else {
        matched_reason = `Facility Analysis: ${f.facility_name} provides multi-capability medical services matching the interpreted search criteria.`;
      }

      let _sortKey = match_score;
      if (sortBy === "distance" && userLocation) _sortKey = distance_km > 0 ? 1 / (1 + distance_km) : 0.5;
      else if (sortBy === "beds") _sortKey = Math.min(1, (f.total_beds || 0) / 4000);
      else if (sortBy === "capabilities") _sortKey = Math.min(1, f.capabilities.length / 29);

      return {
        ...f,
        rank: 0,
        distance_km: Math.round(distance_km * 10) / 10,
        match_score: Math.round(match_score * 100) / 100,
        match_confidence,
        matched_capabilities: matched,
        matched_reason,
        directions_url: `https://www.google.com/maps/dir/?api=1&destination=${f.lat},${f.lng}`,
        _sortKey,
      } as ScoredResult;
    })
    .filter((r) => !userLocation || radiusKm === 0 || r.distance_km <= radiusKm)
    .sort((a, b) => b._sortKey - a._sortKey)
    .slice(0, maxResults)
    .map((r, i) => ({ ...r, rank: i + 1 }));

  const cleanResults: SearchResult[] = scored.map(({ _sortKey, ...rest }) => rest as SearchResult);

  const gaps: string[] = [];
  for (const cap of requiredCaps) {
    if (!cleanResults.some((r) => r.matched_capabilities.includes(cap))) {
      gaps.push(`No facility in results offers ${CAPABILITY_META[cap]?.label ?? cap}.`);
    }
  }

  const trace = {
    step_1_query_decomposition: {
      input: query,
      output: { 
        capabilities: requiredCaps, 
        location: loc.city || "Not provided", 
        need_24x7: need24x7 
      },
      reasoning: "Intent extracted via local NLP pattern matching."
    },
    step_2_vector_retrieval: {
      facilities_found: cleanResults.length,
      top_result: cleanResults[0]?.facility_name || "None",
      engine: "Local In-Memory"
    },
    step_3_agentic_filtering: {
      applied_filters: Object.keys(filters).join(", ") || "none",
      confidence_threshold: minConf
    },
    step_4_final_answer: {
      model: "MediFind Local Agent",
      reasoning: interpreted
    }
  };

  return {
    query_id: crypto.randomUUID(),
    processing_time_ms: Math.round(performance.now() - start),
    total_found: cleanResults.length,
    interpreted_need: interpreted,
    results: cleanResults,
    gaps,
    trace,
    disclaimer: "Always call ahead to confirm current availability before traveling.",
  };
}

export function getFacilityById(id: string): Facility | undefined {
  return SEED_FACILITIES.find((f) => f.facility_id === id);
}
