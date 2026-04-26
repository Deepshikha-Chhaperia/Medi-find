import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { SearchResponse } from "@/types/medifind";
import { searchFacilities } from "@/lib/api";

export type SortBy = "match" | "distance" | "beds" | "capabilities";

interface SearchState {
  // ── Query state ────────────────────────────────────────────────────
  query: string;
  response: SearchResponse | null;
  loading: boolean;
  error: string | null;

  // ── Location ───────────────────────────────────────────────────────
  userLocation: { lat: number; lng: number } | null;
  userCity: string | null;
  locationGranted: boolean;

  // ── Search filters & sorting ───────────────────────────────────────
  radiusKm: number;
  sortBy: SortBy;
  emergencyOnly: boolean;
  minConfidence: number;
  facilityTypeFilter: string | null;

  // ── Compare list ───────────────────────────────────────────────────
  compareList: string[]; // facility_ids (max 3)

  // ── Search history ────────────────────────────────────────────────
  searchHistory: string[]; // last 5 queries (localStorage persisted)

  // ── Actions ───────────────────────────────────────────────────────
  setQuery: (q: string) => void;
  setResponse: (r: SearchResponse | null) => void;
  setLoading: (l: boolean) => void;
  setError: (e: string | null) => void;

  setUserLocation: (l: { lat: number; lng: number } | null) => void;
  setUserCity: (c: string | null) => void;
  setLocationGranted: (v: boolean) => void;

  setRadiusKm: (r: number) => void;
  setSortBy: (s: SortBy) => void;
  setEmergencyOnly: (v: boolean) => void;
  setMinConfidence: (v: number) => void;
  setFacilityTypeFilter: (v: string | null) => void;

  addToCompare: (id: string) => void;
  removeFromCompare: (id: string) => void;
  clearCompare: () => void;

  addToHistory: (q: string) => void;
  clearHistory: () => void;

  // ── Central search action ──────────────────────────────────────────
  search: (q?: string) => Promise<void>;
}

export const useSearchStore = create<SearchState>()(
  persist(
    (set, get) => ({
      // Initial state
      query: "",
      response: null,
      loading: false,
      error: null,
      userLocation: null,
      userCity: null,
      locationGranted: false,
      radiusKm: 50,
      sortBy: "match",
      emergencyOnly: false,
      minConfidence: 0,
      facilityTypeFilter: null,
      compareList: [],
      searchHistory: [],

      // ── Setters ──────────────────────────────────────────────────────
      setQuery: (q) => set({ query: q }),
      setResponse: (r) => set({ response: r }),
      setLoading: (l) => set({ loading: l }),
      setError: (e) => set({ error: e }),

      setUserLocation: (l) => set({ userLocation: l }),
      setUserCity: (c) => set({ userCity: c }),
      setLocationGranted: (v) => set({ locationGranted: v }),

      setRadiusKm: (r) => set({ radiusKm: r }),
      setSortBy: (s) => set({ sortBy: s }),
      setEmergencyOnly: (v) => set({ emergencyOnly: v }),
      setMinConfidence: (v) => set({ minConfidence: v }),
      setFacilityTypeFilter: (v) => set({ facilityTypeFilter: v }),

      addToCompare: (id) => {
        const { compareList } = get();
        if (compareList.length >= 3 || compareList.includes(id)) return;
        set({ compareList: [...compareList, id] });
      },
      removeFromCompare: (id) =>
        set({ compareList: get().compareList.filter((x) => x !== id) }),
      clearCompare: () => set({ compareList: [] }),

      addToHistory: (q) => {
        if (!q.trim()) return;
        const prev = get().searchHistory.filter((h) => h !== q);
        set({ searchHistory: [q, ...prev].slice(0, 5) });
      },
      clearHistory: () => set({ searchHistory: [] }),

      // ── Central search ────────────────────────────────────────────────
      search: async (queryOverride?: string) => {
        const { query: storeQuery, userLocation, radiusKm, sortBy,
                emergencyOnly, minConfidence, facilityTypeFilter, addToHistory } = get();
        const q = (queryOverride ?? storeQuery).trim();
        if (!q) return;

        set({ loading: true, error: null, query: q });
        addToHistory(q);

        try {
          const result = await searchFacilities({
            query: q,
            location: userLocation ?? undefined,
            radius_km: radiusKm,
            sort_by: sortBy,
            filters: {
              emergency_only: emergencyOnly,
              min_confidence: minConfidence,
              facility_type: facilityTypeFilter ?? undefined,
            },
          });
          set({ response: result, loading: false });
        } catch (err: unknown) {
          set({
            error: err instanceof Error ? err.message : "Search failed",
            loading: false,
          });
        }
      },
    }),
    {
      name: "medifind-search-store",
      // Only persist non-volatile fields
      partialize: (s) => ({
        searchHistory: s.searchHistory,
        radiusKm: s.radiusKm,
        sortBy: s.sortBy,
        locationGranted: s.locationGranted,
        compareList: s.compareList,
      }),
    }
  )
);