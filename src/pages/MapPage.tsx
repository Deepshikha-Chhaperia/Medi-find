import { useEffect, useMemo, useState } from "react";
import { MapView } from "@/components/medifind/MapView";
import { useSearchStore } from "@/store/useSearchStore";
import type { Facility, SearchResult } from "@/types/medifind";
import { Filter, MapPin } from "lucide-react";
import { cn } from "@/lib/utils";
import { getCapabilities, listFacilities } from "@/lib/api";

function toResult(f: Facility): SearchResult {
  return {
    ...f,
    emergency_24x7: Boolean(f.emergency_24x7),
    total_beds: f.total_beds || 0,
    icu_beds: f.icu_beds || 0,
    capabilities: f.capabilities || [],
    equipment: f.equipment || [],
    accreditations: f.accreditations || [],
    trust_score: f.trust_score || 1,
    trust_flags: f.trust_flags || [],
    data_age_days: f.data_age_days || 0,
    rank: 0,
    distance_km: 0,
    match_score: f.extraction_confidence || 0.5,
    match_confidence: (f.extraction_confidence || 0) >= 0.75 ? "High" : (f.extraction_confidence || 0) >= 0.5 ? "Medium" : "Low",
    matched_capabilities: f.capabilities || [],
    matched_reason: "Indexed facility profile",
    directions_url: `https://www.google.com/maps/dir/?api=1&destination=${f.lat || 0},${f.lng || 0}`,
  };
}

export default function MapPage() {
  const { userLocation } = useSearchStore();
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [emergencyOnly, setEmergencyOnly] = useState(false);
  const [capabilityFilter, setCapabilityFilter] = useState<string>("all");
  const [capabilityQuery, setCapabilityQuery] = useState("");
  const [capabilities, setCapabilities] = useState<Array<{ id: string; label: string }>>([]);
  const [facilities, setFacilities] = useState<Facility[]>([]);

  useEffect(() => {
    const run = async () => {
      const [capsObj, facs] = await Promise.all([
        getCapabilities(),
        listFacilities({ limit: 200 }),
      ]);
      const capList = Object.entries(capsObj).map(([id, v]) => ({ id, label: v.label || id }));
      setCapabilities(capList.sort((a, b) => a.label.localeCompare(b.label)));
      setFacilities(facs);
    };
    run();
  }, []);

  const facilityTypes = useMemo(() => {
    const types = [...new Set(facilities.map((f) => f.facility_type).filter(Boolean))] as string[];
    return ["all", ...types];
  }, [facilities]);

  const filteredCapabilities = useMemo(() => {
    const q = capabilityQuery.trim().toLowerCase();
    if (!q) return capabilities;
    return capabilities.filter((c) => c.label.toLowerCase().includes(q) || c.id.toLowerCase().includes(q));
  }, [capabilities, capabilityQuery]);

  const filtered = useMemo(() => {
    return facilities
      .filter((f) => {
        if (typeFilter !== "all" && f.facility_type !== typeFilter) return false;
        if (emergencyOnly && !f.emergency_24x7) return false;
        if (capabilityFilter !== "all" && !(f.capabilities || []).includes(capabilityFilter)) return false;
        return true;
      })
      .map(toResult);
  }, [facilities, typeFilter, emergencyOnly, capabilityFilter]);

  const coverageStats = useMemo(() => {
    const stats: Record<string, number> = {};
    for (const f of facilities) {
      for (const cap of f.capabilities || []) {
        stats[cap] = (stats[cap] || 0) + 1;
      }
    }
    return Object.entries(stats)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6)
      .map(([id, count]) => ({ id, label: capabilities.find((c) => c.id === id)?.label ?? id, count }));
  }, [facilities, capabilities]);

  const cities = [...new Set(facilities.map((f) => f.city).filter(Boolean))].length;

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem)]">
      <div className="flex items-center gap-3 border-b border-border bg-surface px-4 py-2.5 shrink-0 overflow-x-auto no-scrollbar">
        <div className="flex items-center gap-1.5 text-[12px] text-muted-foreground shrink-0">
          <MapPin className="h-3.5 w-3.5" />
          {filtered.length} facilities · {cities} cities
        </div>

        <div className="h-4 w-px bg-border" />

        <input
          type="text"
          value={capabilityQuery}
          onChange={(e) => setCapabilityQuery(e.target.value)}
          placeholder="Search treatment..."
          className="bg-surface-muted rounded-md border border-border px-2.5 py-1 text-[12px] focus:outline-none focus:border-accent/40"
        />

        <select
          value={capabilityFilter}
          onChange={(e) => setCapabilityFilter(e.target.value)}
          className="bg-surface-muted rounded-md border border-border px-2.5 py-1 text-[12px] focus:outline-none focus:border-accent/40"
        >
          <option value="all">All treatments</option>
          {filteredCapabilities.map((c) => (
            <option key={c.id} value={c.id}>{c.label}</option>
          ))}
        </select>

        <div className="flex items-center gap-1.5 shrink-0">
          <Filter className="h-3.5 w-3.5 text-muted-foreground" />
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="bg-surface-muted rounded-md border border-border px-2.5 py-1 text-[12px] focus:outline-none focus:border-accent/40"
          >
            {facilityTypes.map((t) => (
              <option key={t} value={t}>{t === "all" ? "All types" : t}</option>
            ))}
          </select>
        </div>

        <button
          onClick={() => setEmergencyOnly((v) => !v)}
          className={cn(
            "shrink-0 inline-flex items-center gap-1.5 rounded-md border px-3 py-1 text-[12px] font-medium transition-colors",
            emergencyOnly
              ? "border-emergency/30 bg-emergency/10 text-emergency"
              : "border-border text-muted-foreground hover:bg-surface-muted"
          )}
        >
          24/7 only
        </button>

        <div className="ml-auto hidden md:flex items-center gap-1.5">
          <span className="text-[11px] text-muted-foreground">Top capabilities:</span>
          {coverageStats.map((s) => (
            <span
              key={s.id}
              className="inline-flex items-center gap-1 rounded-md bg-surface-muted border border-border px-2 py-0.5 text-[11px] font-medium text-muted-foreground"
            >
              {s.label}
              <span className="text-accent font-semibold">{s.count}</span>
            </span>
          ))}
        </div>
      </div>

      <div className="flex-1 relative overflow-hidden">
        <MapView
          results={filtered}
          showUserLocation={!!userLocation}
          userLocation={userLocation}
          radiusKm={0}
          zoom={5}
          center={userLocation ? [userLocation.lat, userLocation.lng] : [20.5937, 78.9629]}
          className="h-full w-full"
        />
      </div>
    </div>
  );
}
