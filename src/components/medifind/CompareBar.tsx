import { X, GitCompare, ChevronRight } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useSearchStore } from "@/store/useSearchStore";
import { cn } from "@/lib/utils";

export function CompareBar() {
  const { compareList, removeFromCompare, clearCompare, response } = useSearchStore();
  const navigate = useNavigate();

  if (compareList.length === 0) return null;

  // Look up names
  const items = compareList.map((id) => ({
    id,
    name: response?.results.find((f) => f.facility_id === id)?.facility_name ?? id.slice(0, 8),
  }));

  return (
    <div className={cn(
      "fixed bottom-20 inset-x-0 z-[9999] flex justify-center px-4 md:bottom-6 animate-fade-in-up pointer-events-none"
    )}>
      <div className="w-full max-w-2xl bg-primary text-primary-foreground rounded-xl shadow-soft-lg flex items-center gap-3 px-4 py-3 pointer-events-auto">
        <GitCompare className="h-4 w-4 shrink-0 text-accent" />
        <div className="flex flex-1 flex-wrap gap-2 min-w-0">
          {items.map((item) => (
            <span
              key={item.id}
              className="inline-flex items-center gap-1 rounded-md bg-white/10 px-2.5 py-0.5 text-xs font-medium"
            >
              <span className="truncate max-w-[140px]">{item.name}</span>
              <button onClick={() => removeFromCompare(item.id)} className="ml-0.5 hover:text-destructive">
                <X className="h-2.5 w-2.5" />
              </button>
            </span>
          ))}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <button
            onClick={clearCompare}
            className="text-xs text-primary-foreground/60 hover:text-primary-foreground"
          >
            Clear
          </button>
          <button
            disabled={compareList.length < 2}
            onClick={() => {
              navigate(`/compare?ids=${compareList.join(",")}`);
              clearCompare();
            }}
            className="inline-flex items-center gap-1 rounded-md bg-accent px-3 py-1.5 text-xs font-semibold text-white hover:bg-accent/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Compare <ChevronRight className="h-3 w-3" />
          </button>
        </div>
      </div>
    </div>
  );
}
