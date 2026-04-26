import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { MapPin, Filter, SlidersHorizontal, ArrowUpDown, AlertCircle,
         BedDouble, Zap, ChevronDown } from "lucide-react";
import { SearchInput } from "@/components/medifind/SearchInput";
import { FacilityCard } from "@/components/medifind/FacilityCard";
import { SkeletonCard } from "@/components/medifind/SkeletonCard";
import { CompareBar } from "@/components/medifind/CompareBar";
import { MapView } from "@/components/medifind/MapView";
import { useSearchStore } from "@/store/useSearchStore";
import type { SortBy } from "@/store/useSearchStore";
import { cn } from "@/lib/utils";
import { reverseGeocode } from "@/lib/geocode";
import { toast } from "sonner";

const RADIUS_OPTIONS = [5, 10, 25, 50, 100, 0] as const; // 0 = no limit
const RADIUS_LABELS: Record<number, string> = {
  5: "5 km", 10: "10 km", 25: "25 km", 50: "50 km", 100: "100 km", 0: "Any",
};

const SORT_OPTIONS: { value: SortBy; label: string }[] = [
  { value: "match", label: "Best match" },
  { value: "distance", label: "Nearest first" },
  { value: "beds", label: "Most beds" },
  { value: "capabilities", label: "Most capabilities" },
];

type ViewMode = "list" | "split";

export default function Results() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const {
    query, setQuery, response, loading, error, search, userLocation, userCity,
    radiusKm, setRadiusKm, sortBy, setSortBy,
    emergencyOnly, setEmergencyOnly, minConfidence, setMinConfidence,
    searchHistory, clearHistory,
    setUserLocation, setUserCity, setLocationGranted
  } = useSearchStore();

  const requestLocation = () => {
    if (!navigator.geolocation) {
      toast.error("Geolocation is not supported by your browser");
      return;
    }
    toast.loading("Finding nearest facilities...", { id: "geo" });
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const loc = { lat: pos.coords.latitude, lng: pos.coords.longitude };
        setUserLocation(loc);
        setRadiusKm(50); // Automatically reset to 50km
        setLocationGranted(true);
        const geo = await reverseGeocode(loc.lat, loc.lng);
        if (geo.city) setUserCity(geo.city);
        toast.success("Location set! Searching nearby...", { id: "geo" });
        await handleSearch(); // trigger a fresh search
      },
      () => {
        toast.error("Location access denied or unavailable.", { id: "geo" });
      },
      { timeout: 8000 }
    );
  };

  const [view, setView] = useState<ViewMode>("split");
  const [filtersOpen, setFiltersOpen] = useState(false);

  // ── Read URL params on mount ──────────────────────────────────────────────
  useEffect(() => {
    const urlQ = searchParams.get("q") || "";
    const urlRadius = parseInt(searchParams.get("radius") || "50") || 50;
    const urlSort = (searchParams.get("sort") || "match") as SortBy;

    if (urlQ && urlQ !== query) {
      setQuery(urlQ);
      setRadiusKm(urlRadius);
      setSortBy(urlSort);
      // Search with URL params
      search(urlQ);
    } else if (!response && query) {
      search();
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Write URL params on search ────────────────────────────────────────────
  const handleSearch = async (q?: string) => {
    const finalQ = q ?? query;
    if (!finalQ.trim()) return;
    setSearchParams({ q: finalQ, radius: String(radiusKm), sort: sortBy });
    await search(finalQ);
  };

  // Re-trigger search instantly if filters change
  useEffect(() => {
    if (response) {
      handleSearch();
    }
  }, [radiusKm, sortBy, emergencyOnly, minConfidence]);

  const results = response?.results ?? [];
  const gaps = response?.gaps ?? [];

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      {/* Search bar */}
      <div className="border-b border-border bg-surface px-4 py-3 shrink-0">
        <div className="max-w-5xl mx-auto space-y-2">
          <SearchInput
            value={query}
            onChange={setQuery}
            onSubmit={() => handleSearch()}
            loading={loading}
            hasLocation={!!userLocation}
            onUseLocation={requestLocation}
            history={searchHistory}
            onSelectHistory={(q) => handleSearch(q)}
            onClearHistory={clearHistory}
          />

          {/* Filter bar */}
          <div className="flex items-center gap-2 overflow-x-auto pb-0.5 no-scrollbar">
            {/* Sort */}
            <div className="relative shrink-0">
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as SortBy)}
                className="appearance-none rounded-md border border-border bg-surface-muted px-3 py-1.5 pr-7 text-[12px] font-medium text-foreground focus:outline-none focus:border-accent/40"
              >
                {SORT_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
              <ArrowUpDown className="absolute right-2 top-1/2 -translate-y-1/2 h-3 w-3 text-muted-foreground pointer-events-none" />
            </div>

            {/* Radius */}
            <div className="relative shrink-0">
              <select
                value={radiusKm}
                onChange={(e) => setRadiusKm(Number(e.target.value))}
                className="appearance-none rounded-md border border-border bg-surface-muted px-3 py-1.5 pr-7 text-[12px] font-medium text-foreground focus:outline-none focus:border-accent/40"
              >
                {RADIUS_OPTIONS.map((r) => (
                  <option key={r} value={r}>{RADIUS_LABELS[r]}</option>
                ))}
              </select>
              <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 h-3 w-3 text-muted-foreground pointer-events-none" />
            </div>

            {/* Emergency only toggle */}
            <button
              onClick={() => setEmergencyOnly(!emergencyOnly)}
              className={cn(
                "shrink-0 inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-[12px] font-medium transition-colors",
                emergencyOnly
                  ? "border-emergency/30 bg-emergency/10 text-emergency"
                  : "border-border text-muted-foreground hover:bg-surface-muted"
              )}
            >
              <Zap className="h-3.5 w-3.5" />
              24/7 Only
            </button>

            {/* Min confidence */}
            <div className="flex items-center gap-2 shrink-0">
              <SlidersHorizontal className="h-3.5 w-3.5 text-muted-foreground" />
              <input
                type="range" min="0" max="1" step="0.05"
                value={minConfidence}
                onChange={(e) => setMinConfidence(parseFloat(e.target.value))}
                className="w-20 accent-accent"
              />
              <span className="text-[11px] font-mono text-muted-foreground w-6">
                {Math.round(minConfidence * 100)}%
              </span>
            </div>

            {/* View toggle */}
            <div className="ml-auto flex shrink-0 items-center gap-1 rounded-lg border border-border p-0.5">
              {(["list", "split"] as const).map((v) => (
                <button
                  key={v}
                  onClick={() => setView(v)}
                  className={cn(
                    "rounded-md px-3 py-1 text-[12px] font-medium transition-colors capitalize",
                    view === v ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"
                  )}
                >
                  {v}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Results */}
      <div className={cn(
        "flex-1 overflow-hidden",
        view === "split" ? "grid grid-cols-1 md:grid-cols-2" : "flex flex-col"
      )}>
        {/* List pane */}
        <div className="overflow-y-auto px-4 py-4">
          <div className="max-w-2xl mx-auto space-y-3">
            {/* Header */}
            <div className="flex items-center justify-between">
              <div>
                {userCity && (
                  <div className="flex items-center gap-1 text-[12px] text-muted-foreground mb-1">
                    <MapPin className="h-3 w-3" />
                    Results near <span className="text-foreground font-medium">{userCity}</span>
                  </div>
                )}
                {response && (
                  <p className="text-[12px] text-muted-foreground font-mono">
                    {response.total_found} results · {response.processing_time_ms}ms
                  </p>
                )}
              </div>
            </div>

            {/* Interpreted query */}
            {response?.interpreted_need && (
              <div className="rounded-lg bg-accent-soft/50 border border-accent/10 px-4 py-2.5">
                <p className="text-[12px] text-foreground">
                  <span className="font-medium text-accent">Searching for:</span>{" "}
                  {response.interpreted_need}
                </p>
              </div>
            )}

            {/* Gap banner */}
            {gaps.length > 0 && (
              <div className="rounded-lg bg-destructive/5 border border-destructive/20 px-4 py-3">
                <div className="flex items-start gap-2">
                  <AlertCircle className="h-4 w-4 text-destructive shrink-0 mt-0.5" />
                  <div>
                    <p className="text-[12px] font-semibold text-destructive mb-0.5">Coverage Gap Detected</p>
                    {gaps.slice(0, 2).map((g, i) => (
                      <p key={i} className="text-[11px] text-destructive/80">{g}</p>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Agent Traceability (Chain of Thought) */}
            {response?.trace && (
              <details className="group rounded-lg border border-border bg-surface-muted px-4 py-2 [&_summary::-webkit-details-marker]:hidden">
                <summary className="flex cursor-pointer items-center justify-between font-medium text-[12px] text-muted-foreground outline-none">
                  <span className="flex items-center gap-2">
                    <SlidersHorizontal className="h-3.5 w-3.5" />
                    How did we find this? (Agent Trace)
                  </span>
                  <ChevronDown className="h-4 w-4 transition-transform group-open:rotate-180" />
                </summary>
                <div className="mt-3 overflow-auto max-h-64 no-scrollbar border-t border-border pt-3">
                  <pre className="text-[10px] sm:text-[11px] font-mono text-muted-foreground bg-surface rounded-md p-3 border border-border/50">
                    {JSON.stringify(response.trace, null, 2)}
                  </pre>
                </div>
              </details>
            )}

            {/* Skeletons while loading */}
            {loading && Array.from({ length: 4 }).map((_, i) => (
              <SkeletonCard key={i} />
            ))}

            {/* Error */}
            {error && !loading && (
              <div className="rounded-xl border border-destructive/20 bg-destructive/5 p-6 text-center">
                <AlertCircle className="h-8 w-8 text-destructive mx-auto mb-2" />
                <p className="text-sm font-medium text-destructive">{error}</p>
              </div>
            )}

            {/* Results */}
            {!loading && results.map((r, i) => (
              <FacilityCard key={r.facility_id} result={r} index={i} />
            ))}

            {/* Empty state (Navigating the Truth Gap) */}
            {!loading && !error && response && results.length === 0 && (
              <div className="rounded-xl border border-warning/50 bg-warning/5 p-8 text-center space-y-4">
                <AlertCircle className="h-10 w-10 text-warning mx-auto" />
                <div>
                  <h3 className="font-serif text-[22px] font-semibold text-foreground mb-2">Zero Matches Found</h3>
                  <p className="font-sans text-[14px] text-muted-foreground max-w-md mx-auto leading-relaxed">
                    We scanned the dataset. No facility {userCity ? `in or near ${userCity} ` : ''}possesses verified capability for <strong className="text-foreground font-medium">{response.interpreted_need || query}</strong>.
                  </p>
                </div>
                <div className="pt-5 mt-5 border-t border-warning/20">
                  <p className="text-[11px] uppercase tracking-wider text-warning/80 font-semibold mb-4">Recommended Actions</p>
                  <div className="flex flex-wrap justify-center gap-3">
                    <button
                      onClick={() => { setRadiusKm(0); handleSearch(); }}
                      className="rounded-full bg-surface px-5 py-2.5 text-[13px] font-medium text-foreground hover:bg-surface-muted border border-border shadow-sm transition-colors"
                    >
                      Expand to Nationwide Index
                    </button>
                    <button
                      onClick={() => { setQuery(""); document.querySelector('input')?.focus(); }}
                      className="rounded-full bg-primary px-5 py-2.5 text-[13px] font-medium text-primary-foreground hover:bg-primary/90 shadow-sm transition-colors"
                    >
                      Search alternative procedure
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Map pane */}
        {view === "split" && (
          <div className="hidden md:block border-l border-border h-full">
            <MapView
              results={results}
              showUserLocation={!!userLocation}
              userLocation={userLocation}
              radiusKm={radiusKm > 0 ? radiusKm : 0}
              className="h-full w-full"
            />
          </div>
        )}
      </div>

      {/* Compare floating bar */}
      <CompareBar />
    </div>
  );
}