import { useState, useRef, useEffect } from "react";
import { Search, MapPin, Mic, Loader2, ArrowUpRight, X, Clock } from "lucide-react";
import { cn } from "@/lib/utils";

interface Props {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  onUseLocation?: () => void;
  loading?: boolean;
  hasLocation?: boolean;
  large?: boolean;
  placeholder?: string;
  autoFocus?: boolean;
  history?: string[];
  onSelectHistory?: (q: string) => void;
  onClearHistory?: () => void;
}

export function SearchInput({
  value, onChange, onSubmit, onUseLocation, loading,
  hasLocation, large, placeholder, autoFocus,
  history = [], onSelectHistory, onClearHistory,
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const [listening, setListening] = useState(false);
  const [showHistory, setShowHistory] = useState(false);

  useEffect(() => {
    if (autoFocus) inputRef.current?.focus();
  }, [autoFocus]);

  // Close history on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setShowHistory(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const handleVoice = () => {
    const SR = (window as Record<string, unknown>).SpeechRecognition as typeof SpeechRecognition ||
               (window as Record<string, unknown>).webkitSpeechRecognition as typeof SpeechRecognition;
    if (!SR) return;
    const rec = new SR();
    rec.lang = "en-IN";
    rec.onstart = () => setListening(true);
    rec.onend = () => setListening(false);
    rec.onresult = (e: SpeechRecognitionEvent) => {
      onChange(e.results[0][0].transcript);
    };
    rec.start();
  };

  const hasHistory = history.length > 0;

  return (
    <div ref={wrapRef} className="relative w-full">
      <form
        onSubmit={(e) => { e.preventDefault(); setShowHistory(false); onSubmit(); }}
        className={cn(
          "group relative flex items-center gap-2 rounded-full border border-border bg-surface transition-all overflow-hidden",
          large
            ? "p-2 pl-6 shadow-sm focus-within:ring-2 focus-within:ring-border"
            : "p-1.5 pl-4 shadow-sm focus-within:ring-2 focus-within:ring-border",
        )}
      >
        <Search className={cn("shrink-0 text-muted-foreground", large ? "h-5 w-5" : "h-4 w-4")} />
        <input
          ref={inputRef}
          value={value}
          onChange={(e) => { onChange(e.target.value); setShowHistory(true); }}
          onFocus={() => hasHistory && setShowHistory(true)}
          placeholder={placeholder ?? "Describe what you need… e.g. NICU near Kolkata 24 hours"}
          className={cn(
            "flex-1 bg-transparent font-sans outline-none placeholder:text-muted-foreground text-foreground",
            large ? "h-12 text-[15px]" : "h-9 text-sm"
          )}
        />

        {/* Clear button */}
        {value && (
          <button
            type="button"
            onClick={() => { onChange(""); inputRef.current?.focus(); }}
            className="hidden sm:inline-flex items-center justify-center rounded-full p-1.5 text-muted-foreground hover:bg-surface-muted hover:text-foreground transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        )}

        {/* Location */}
        <button
          type="button"
          onClick={onUseLocation}
          title={hasLocation ? "Location set" : "Use my location"}
          className={cn(
            "hidden sm:inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[13px] font-sans font-medium transition-colors",
            hasLocation
              ? "bg-surface-muted text-foreground"
              : "text-muted-foreground hover:bg-surface-muted hover:text-foreground"
          )}
        >
          <MapPin className="h-4 w-4" />
          {hasLocation ? "Located" : "Locate"}
        </button>

        {/* Voice */}
        <button
          type="button"
          onClick={handleVoice}
          title="Voice input"
          className={cn(
            "hidden sm:inline-flex items-center justify-center rounded-full p-2.5 text-muted-foreground hover:bg-surface-muted hover:text-foreground transition-colors",
            listening && "bg-destructive/10 text-destructive"
          )}
        >
          <Mic className="h-4 w-4" />
        </button>

        <button
          type="submit"
          disabled={loading || !value.trim()}
          className={cn(
            "inline-flex items-center gap-1.5 rounded-full bg-primary text-primary-foreground font-sans font-medium transition-all hover:bg-primary/95 disabled:opacity-50 disabled:cursor-not-allowed ml-1",
            large ? "h-12 px-6 text-[15px]" : "h-9 px-4 text-sm"
          )}
        >
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <>Search <ArrowUpRight className="h-4 w-4" /></>}
        </button>
      </form>

      {/* History dropdown */}
      {showHistory && hasHistory && !value && (
        <div className="absolute top-full left-0 right-0 mt-1.5 z-50 rounded-xl border border-border bg-surface shadow-soft-md overflow-hidden animate-fade-in-up">
          <div className="flex items-center justify-between px-3 py-2 border-b border-border">
            <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">Recent searches</span>
            {onClearHistory && (
              <button onClick={onClearHistory} className="text-[11px] text-muted-foreground hover:text-foreground">
                Clear all
              </button>
            )}
          </div>
          {history.map((h, i) => (
            <button
              key={i}
              onClick={() => {
                onChange(h);
                setShowHistory(false);
                onSelectHistory?.(h);
              }}
              className="flex w-full items-center gap-3 px-3 py-2.5 text-sm text-foreground hover:bg-surface-muted transition-colors"
            >
              <Clock className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
              <span className="truncate">{h}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}