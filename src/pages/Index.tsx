import { useEffect, useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { AlertTriangle, MapPin, Loader2, Edit2, Check, Navigation } from "lucide-react";
import { SearchInput } from "@/components/medifind/SearchInput";
import { useSearchStore } from "@/store/useSearchStore";
import { reverseGeocode } from "@/lib/geocode";
import { QUICK_SEARCHES } from "@/data/capabilities";

export default function Index() {
  const navigate = useNavigate();
  const {
    query, setQuery, search, loading,
    userLocation, setUserLocation, setUserCity, userCity, setLocationGranted,
    searchHistory, addToHistory, clearHistory,
  } = useSearchStore();

  const [locationLoading, setLocationLoading] = useState(false);
  const [editingLocation, setEditingLocation] = useState(false);
  const [manualCity, setManualCity] = useState(userCity || "");
  const locInputRef = useRef<HTMLInputElement>(null);

  // We do NOT silently auto-request on mount anymore to avoid forcing Delhi
  // Let the user click "Locate me" or type manually.

  const handleUseLocation = () => {
    if (!navigator.geolocation) return;
    setLocationLoading(true);
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const loc = { lat: pos.coords.latitude, lng: pos.coords.longitude };
        setUserLocation(loc);
        setLocationGranted(true);
        setLocationLoading(false);
        const geo = await reverseGeocode(loc.lat, loc.lng);
        if (geo.city) {
          setUserCity(geo.city);
          setManualCity(geo.city);
        }
      },
      () => {
        setLocationLoading(false);
        setEditingLocation(true); // Fallback to manual entry if blocked
      },
      { timeout: 8000 }
    );
  };

  const saveManualLocation = () => {
    if (manualCity.trim()) {
      setUserCity(manualCity.trim());
      // Clear exact lat/lng so the backend relies purely on city text match
      setUserLocation(null); 
      setEditingLocation(false);
    }
  };

  const handleSearch = async (q?: string) => {
    const finalQ = q ?? query;
    if (!finalQ.trim()) return;
    await search(finalQ);
    navigate(`/results?q=${encodeURIComponent(finalQ)}`);
  };

  const handleEmergency = () => {
    const q = "nearest 24/7 hospital emergency ICU blood bank";
    setQuery(q);
    handleSearch(q);
  };

  return (
    <div className="flex flex-col min-h-[calc(100vh-4rem)] bg-background">
      <div className="relative flex-1 flex flex-col items-center justify-center px-4 pt-10 pb-20">
        
        <div className="w-full max-w-4xl space-y-8 animate-fade-in-up">
          {/* Agentic Search Pill */}
          <div className="flex justify-center mb-10">
            <div className="inline-flex items-center gap-2 rounded-full border border-border bg-surface/50 backdrop-blur-md px-4 py-1.5 text-[13px] font-medium text-foreground shadow-sm">
              <span className="h-1.5 w-1.5 rounded-full bg-accent" />
              Agentic search across 10k facility reports
            </div>
          </div>

          {/* Minimalist Heading */}
          <div className="text-center">
            <h1 className="font-sans font-semibold text-[56px] sm:text-[80px] text-foreground tracking-tight leading-[0.95] mb-2">
              Find life-saving care.
            </h1>
            <p className="font-serif italic text-[50px] sm:text-[76px] text-muted-foreground leading-none mb-8">
              Not confusion.
            </p>
            <p className="font-sans text-muted-foreground text-[18px] sm:text-[21px] text-center mb-12 max-w-2xl leading-relaxed font-normal mx-auto">
              MediFind reads thousands of unstructured hospital reports and answers in plain English.
            </p>
          </div>

          {/* Search Box - Large and Centered */}
          <div className="mx-auto max-w-2xl">
            <SearchInput
              value={query}
              onChange={setQuery}
              onSubmit={() => handleSearch()}
              onUseLocation={handleUseLocation}
              loading={loading}
              hasLocation={!!userLocation || !!userCity}
              large
              autoFocus
              history={searchHistory}
              onSelectHistory={(q) => handleSearch(q)}
              onClearHistory={clearHistory}
            />
          </div>

          {/* SOS Button */}
           <div className="flex justify-center">
            <button
              onClick={handleEmergency}
              className="group flex items-center gap-2.5 rounded-full bg-emergency/10 border border-emergency/20 px-6 py-2.5 text-sm font-semibold text-emergency hover:bg-emergency hover:text-white transition-all shadow-sm"
            >
              <AlertTriangle className="h-4 w-4" />
              Emergency SOS: Find Nearest 24/7 Centre
            </button>
          </div>

          {/* Location Bar & Quick Searches */}
          <div className="mt-8 flex flex-col items-center space-y-4">
            
            {/* Programmable Location Badge */}
            <div className="flex items-center gap-2">
              {editingLocation ? (
                <div className="flex items-center gap-1.5 rounded-md border border-accent/40 bg-surface px-2 py-1 shadow-sm">
                  <MapPin className="h-3.5 w-3.5 text-muted-foreground" />
                  <input
                    ref={locInputRef}
                    autoFocus
                    value={manualCity}
                    onChange={(e) => setManualCity(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && saveManualLocation()}
                    placeholder="Enter city or ZIP..."
                    className="w-32 bg-transparent text-sm outline-none text-foreground placeholder:text-muted-foreground"
                  />
                  <button onClick={saveManualLocation} className="text-accent hover:text-accent/80 p-1">
                    <Check className="h-3.5 w-3.5" />
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setEditingLocation(true)}
                  className="inline-flex items-center gap-1.5 rounded-md bg-surface-muted px-3 py-1.5 text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-surface transition-colors border border-border"
                  title="Change search location"
                >
                  {locationLoading ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Navigation className="h-3.5 w-3.5" />
                  )}
                  {userCity ? `Near ${userCity}` : "Set Location"}
                  <Edit2 className="h-3 w-3 ml-1 opacity-50" />
                </button>
              )}
            </div>

            <div className="flex flex-wrap justify-center gap-2 max-w-2xl">
              {QUICK_SEARCHES.slice(0, 5).map((qs) => (
                <button
                  key={qs.label}
                  onClick={() => { setQuery(qs.query); handleSearch(qs.query); }}
                  className="rounded-full border border-border bg-surface px-3 py-1 text-[13px] text-muted-foreground hover:border-foreground/30 hover:text-foreground transition-colors"
                >
                  {qs.label}
                </button>
              ))}
            </div>

          </div>
        </div>
      </div>
    </div>
  );
}
