/**
 * MediFind API client.
 * Uses the FastAPI backend when available, but can fall back to a public Google Sheet dataset
 * for static/serverless-friendly deployments.
 */
import type { SearchResponse, Facility } from "@/types/medifind";
import { CAPABILITY_META } from "@/data/capabilities";
import { runSearch } from "@/lib/searchEngine";

const API_URL = import.meta.env.VITE_API_URL ||
  (typeof window !== "undefined" && window.location.hostname === "localhost" && window.location.port === "5173"
    ? "http://localhost:8000"
    : "");

const USE_BACKEND = String(import.meta.env.VITE_USE_BACKEND || "false").toLowerCase() === "true";
const DEFAULT_SHEET_URL =
  import.meta.env.VITE_GOOGLE_SHEET_URL ||
  "https://docs.google.com/spreadsheets/d/1ZDuDmoQlyxZIEahDBlrMjf2wiWG7xU81/edit?gid=1028775758#gid=1028775758";
const DEFAULT_SHEET_GID = import.meta.env.VITE_GOOGLE_SHEET_GID || "1028775758";
const SNAPSHOT_PATH = "/google-sheet-facilities.json";

interface SearchParams {
  query: string;
  location?: { lat: number; lng: number };
  radius_km?: number;
  sort_by?: string;
  filters?: {
    emergency_only?: boolean;
    min_confidence?: number;
    facility_type?: string;
  };
  max_results?: number;
}

interface PublicFacilitiesPayload {
  sheet_url: string;
  gid: string;
  csv_url: string;
  total_rows: number;
  facilities: Facility[];
}

let facilitiesCache: Promise<Facility[]> | null = null;

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body.slice(0, 200)}`);
  }
  return res.json();
}

async function publicDataFetch<T>(path: string): Promise<T> {
  const candidates = USE_BACKEND
    ? [`${API_URL}${path}`]
    : [
        path,
        ...(API_URL ? [`${API_URL}${path}`] : []),
      ];

  let lastError: unknown = null;
  for (const candidate of candidates) {
    try {
      const res = await fetch(candidate, { headers: { "Content-Type": "application/json" } });
      if (!res.ok) {
        lastError = new Error(`API ${res.status}: ${(await res.text()).slice(0, 200)}`);
        continue;
      }
      return res.json();
    } catch (error) {
      lastError = error;
    }
  }

  throw lastError instanceof Error ? lastError : new Error("Public data fetch failed");
}

async function snapshotFetch<T>(path: string): Promise<T> {
  const res = await fetch(path, { headers: { "Content-Type": "application/json" } });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Snapshot ${res.status}: ${body.slice(0, 200)}`);
  }
  return res.json();
}

function computeStatsFromFacilities(facilities: Facility[]) {
  const capCount = facilities.reduce((sum, facility) => sum + (facility.capabilities?.length || 0), 0);
  const avgConfidence = facilities.length
    ? facilities.reduce((sum, facility) => sum + (facility.extraction_confidence || 0), 0) / facilities.length
    : 0;

  return {
    connected: true,
    total_documents: facilities.length,
    total_facilities: facilities.length,
    total_capabilities_indexed: capCount,
    avg_extraction_confidence: avgConfidence,
  };
}

function computeCapabilityGaps(facilities: Facility[]) {
  const byDistrict = new Map<string, { district: string; state: string; capabilities: Set<string> }>();

  for (const facility of facilities) {
    const district = facility.district || facility.city || "Unknown";
    const state = facility.state || "Unknown";
    const key = `${state}::${district}`;
    const entry = byDistrict.get(key) || { district, state, capabilities: new Set<string>() };
    for (const capability of facility.capabilities || []) {
      entry.capabilities.add(capability);
    }
    byDistrict.set(key, entry);
  }

  const allCapabilities = Object.keys(CAPABILITY_META);
  return {
    gaps: Array.from(byDistrict.values())
      .map((entry) => ({
        district: entry.district,
        state: entry.state,
        missing: allCapabilities.filter((capability) => !entry.capabilities.has(capability)).slice(0, 6),
      }))
      .filter((entry) => entry.missing.length > 0)
      .slice(0, 25),
  };
}

async function loadPublicFacilities(forceRefresh = false, params?: { sheet_url?: string; gid?: string; limit?: number }): Promise<Facility[]> {
  if (!forceRefresh && facilitiesCache) return facilitiesCache;

  facilitiesCache = (async () => {
    if (!USE_BACKEND && !params?.sheet_url && !params?.gid && typeof params?.limit !== "number") {
      try {
        const payload = await snapshotFetch<PublicFacilitiesPayload>(SNAPSHOT_PATH);
        return payload.facilities;
      } catch {
        // Fall through to backend/public endpoint attempts.
      }
    }

    const query = new URLSearchParams();
    query.set("sheet_url", params?.sheet_url || DEFAULT_SHEET_URL);
    query.set("gid", params?.gid || DEFAULT_SHEET_GID);
    if (typeof params?.limit === "number") query.set("limit", String(params.limit));

    try {
      const payload = await publicDataFetch<PublicFacilitiesPayload>(`/api/public/facilities?${query.toString()}`);
      return payload.facilities;
    } catch (error) {
      throw error instanceof Error ? error : new Error("Unable to load Google Sheet facilities");
    }
  })();

  return facilitiesCache;
}

function filterFacilities(facilities: Facility[], params?: {
  q?: string;
  capability?: string;
  state?: string;
  district?: string;
  facility_type?: string;
  emergency_only?: boolean;
  limit?: number;
  offset?: number;
}) {
  const query = params?.q?.toLowerCase().trim();
  const capability = params?.capability?.toLowerCase().trim();
  const filtered = facilities.filter((facility) => {
    if (params?.state && facility.state !== params.state) return false;
    if (params?.district && (facility.district || facility.city) !== params.district) return false;
    if (params?.facility_type && facility.facility_type !== params.facility_type) return false;
    if (params?.emergency_only && !facility.emergency_24x7) return false;
    if (capability && !(facility.capabilities || []).some((item) => item.toLowerCase() === capability)) return false;

    if (query) {
      const haystack = [
        facility.facility_name,
        facility.address,
        facility.city,
        facility.state,
        facility.source_excerpt,
        ...(facility.capabilities || []),
        ...(facility.equipment || []),
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      if (!haystack.includes(query)) return false;
    }

    return true;
  });

  const offset = params?.offset ?? 0;
  const limit = params?.limit ?? 200;
  return filtered.slice(offset, offset + limit);
}

export async function searchFacilities(params: SearchParams): Promise<SearchResponse> {
  if (USE_BACKEND) {
    try {
      return await apiFetch<SearchResponse>("/api/search", {
        method: "POST",
        body: JSON.stringify(params),
      });
    } catch {
      // Fall through to local mode.
    }
  }

  const facilities = await loadPublicFacilities(false);
  return runSearch({
    facilities,
    query: params.query,
    userLocation: params.location,
    radiusKm: params.radius_km,
    sortBy: params.sort_by as "match" | "distance" | "beds" | "capabilities" | undefined,
    emergencyOnly: params.filters?.emergency_only,
    minConfidence: params.filters?.min_confidence,
    filters: params.filters,
    maxResults: params.max_results,
  });
}

export async function getFacility(id: string): Promise<Facility | null> {
  if (USE_BACKEND) {
    try {
      return await apiFetch<Facility>(`/api/facilities/${id}`);
    } catch {
      // Fall through to local mode.
    }
  }

  const facilities = await loadPublicFacilities(false);
  return facilities.find((facility) => facility.facility_id === id) || null;
}

export async function getStats(): Promise<Record<string, unknown>> {
  if (USE_BACKEND) {
    try {
      return await apiFetch<Record<string, unknown>>("/api/stats");
    } catch {
      // Fall through to local mode.
    }
  }

  const facilities = await loadPublicFacilities(false);
  return computeStatsFromFacilities(facilities);
}

export async function ingestFiles(files: File[]): Promise<{ job_id: string }> {
  const form = new FormData();
  files.forEach((file) => form.append("files", file));
  const res = await fetch(`${API_URL}/api/ingest`, { method: "POST", body: form });
  if (!res.ok) throw new Error(`Ingest failed: ${res.status}`);
  return res.json();
}

export async function getIngestStatus(jobId: string) {
  if (USE_BACKEND) {
    return apiFetch<Record<string, unknown>>(`/api/ingest/status/${jobId}`);
  }
  return {
    job_id: jobId,
    status: "COMPLETE",
    total_files: 1,
    processed_files: 1,
    failed_files: 0,
    pct_complete: 100,
  };
}

export async function ingestGoogleSheet(params?: {
  sheet_url?: string;
  gid?: string;
  limit?: number;
}): Promise<{
  job_id: string;
  status: string;
  source: string;
  sheet_url: string;
  gid: string;
  total_rows: number;
  completed_rows?: number;
  failed_rows?: number;
  csv_url?: string;
  errors?: string[];
  execution_mode?: string;
}> {
  if (USE_BACKEND) {
    const qp = new URLSearchParams();
    if (params?.sheet_url) qp.set("sheet_url", params.sheet_url);
    if (params?.gid) qp.set("gid", params.gid);
    if (typeof params?.limit === "number") qp.set("limit", String(params.limit));
    const suffix = qp.toString() ? `?${qp.toString()}` : "";
    try {
      return await apiFetch(`/api/ingest/google-sheet${suffix}`, { method: "POST" });
    } catch {
      // Fall through to public mode.
    }
  }

  const isDefaultSource =
    (!params?.sheet_url || params.sheet_url === DEFAULT_SHEET_URL) &&
    (!params?.gid || params.gid === DEFAULT_SHEET_GID) &&
    typeof params?.limit !== "number";

  const facilities = isDefaultSource
    ? await loadPublicFacilities(true)
    : await loadPublicFacilities(true, params);

  return {
    job_id: `public-sheet-${Date.now()}`,
    status: "COMPLETE",
    source: isDefaultSource ? "google_sheet_snapshot" : "google_sheet_public",
    sheet_url: params?.sheet_url || DEFAULT_SHEET_URL,
    gid: params?.gid || DEFAULT_SHEET_GID,
    total_rows: facilities.length,
    completed_rows: facilities.length,
    failed_rows: 0,
    execution_mode: "public-inline",
    errors: [],
  };
}

export async function getIngestSources(limit = 10): Promise<{
  sources: Array<{
    id: number;
    job_id: string | null;
    source_type: string;
    source_url: string | null;
    gid: string | null;
    csv_url: string | null;
    rows_fetched: number;
    rows_inserted: number;
    rows_failed: number;
    status: string;
    message: string | null;
    started_at: string;
    completed_at: string | null;
  }>;
}> {
  if (USE_BACKEND) {
    try {
      return await apiFetch(`/api/ingest/source-status?limit=${limit}`);
    } catch {
      // Fall through to public mode.
    }
  }

  const facilities = await loadPublicFacilities(false);
  const now = new Date().toISOString();
  return {
    sources: [{
      id: 1,
      job_id: null,
      source_type: "google_sheet_snapshot",
      source_url: DEFAULT_SHEET_URL,
      gid: DEFAULT_SHEET_GID,
      csv_url: SNAPSHOT_PATH,
      rows_fetched: facilities.length,
      rows_inserted: facilities.length,
      rows_failed: 0,
      status: "READY",
      message: "Loaded from bundled Google Sheet snapshot.",
      started_at: now,
      completed_at: now,
    }],
  };
}

export async function listFacilities(params?: {
  q?: string;
  capability?: string;
  state?: string;
  district?: string;
  facility_type?: string;
  emergency_only?: boolean;
  limit?: number;
  offset?: number;
}): Promise<Facility[]> {
  if (USE_BACKEND) {
    const qp = new URLSearchParams();
    if (params?.q) qp.set("q", params.q);
    if (params?.capability) qp.set("capability", params.capability);
    if (params?.state) qp.set("state", params.state);
    if (params?.district) qp.set("district", params.district);
    if (params?.facility_type) qp.set("facility_type", params.facility_type);
    if (params?.emergency_only) qp.set("emergency_only", "true");
    qp.set("limit", String(params?.limit ?? 200));
    qp.set("offset", String(params?.offset ?? 0));
    const suffix = qp.toString() ? `?${qp.toString()}` : "";

    try {
      return await apiFetch<Facility[]>(`/api/facilities${suffix}`);
    } catch {
      // Fall through to public mode.
    }
  }

  const facilities = await loadPublicFacilities(false);
  return filterFacilities(facilities, params);
}

export async function getCapabilities(): Promise<Record<string, { label: string; aliases: string[]; category: string }>> {
  if (USE_BACKEND) {
    try {
      return await apiFetch<Record<string, { label: string; aliases: string[]; category: string }>>("/api/capabilities");
    } catch {
      // Fall through to local mode.
    }
  }
  return CAPABILITY_META;
}

export async function getCapabilityGaps(): Promise<{ gaps: Array<{ district: string; state: string; missing: string[] }> }> {
  if (USE_BACKEND) {
    try {
      return await apiFetch<{ gaps: Array<{ district: string; state: string; missing: string[] }> }>("/api/capabilities/gaps");
    } catch {
      // Fall through to local mode.
    }
  }

  const facilities = await loadPublicFacilities(false);
  return computeCapabilityGaps(facilities);
}
