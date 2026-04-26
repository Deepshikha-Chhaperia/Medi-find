import { SearchResult } from "@/types/medifind";
import { CapabilityChip } from "./CapabilityChip";
import { ConfidenceDot } from "./ConfidenceDot";
import { ShareButton } from "./ShareButton";
import {
  Phone, Navigation, Clock, BedDouble, ShieldCheck, FileText, ArrowRight, GitCompare, Check, AlertCircle
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Link } from "react-router-dom";
import { useSearchStore } from "@/store/useSearchStore";

interface Props {
  result: SearchResult;
  showRank?: boolean;
  index?: number;
}

export function FacilityCard({ result, showRank = true, index = 0 }: Props) {
  const { compareList, addToCompare, removeFromCompare } = useSearchStore();
  const inCompare = compareList.includes(result.facility_id);
  const compareFull = compareList.length >= 3 && !inCompare;

  const toggleCompare = (e: React.MouseEvent) => {
    e.stopPropagation();
    inCompare ? removeFromCompare(result.facility_id) : addToCompare(result.facility_id);
  };

  return (
    <article
      className="group relative rounded-xl border border-border bg-surface p-5 transition-all hover:border-foreground/20 hover:shadow-soft-md animate-fade-in-up"
      style={{ animationDelay: `${index * 60}ms` }}
    >
      {/* Compare checkbox — top right absolute */}
      <button
        onClick={toggleCompare}
        disabled={compareFull}
        title={inCompare ? "Remove from compare" : compareFull ? "Max 3 facilities" : "Add to compare"}
        className={cn(
          "absolute top-3 right-3 flex h-5 w-5 items-center justify-center rounded border transition-colors",
          inCompare
            ? "border-accent bg-accent text-white"
            : compareFull
            ? "border-border text-muted-foreground opacity-30"
            : "border-border text-transparent hover:border-accent/50"
        )}
      >
        <Check className="h-3 w-3" strokeWidth={3} />
      </button>

      {/* Header */}
      <div className="flex items-start justify-between gap-4 pr-8">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1.5">
            {showRank && (
              <span className="font-mono text-[11px] font-medium text-muted-foreground tabular-nums">
                #{result.rank.toString().padStart(2, "0")}
              </span>
            )}
            <span className="text-[11px] font-medium text-muted-foreground">
              {result.facility_type}
            </span>
            {result.emergency_24x7 && (
              <span className="inline-flex items-center gap-1 rounded-md bg-emergency/10 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-emergency">
                <Clock className="h-2.5 w-2.5" /> 24/7
              </span>
            )}
          </div>
          <div className="block">
            <h3 className="text-[17px] font-semibold tracking-tight text-foreground group-hover:text-accent transition-colors">
              {result.facility_name}
            </h3>
          </div>
          <p className="mt-1 text-[13px] text-muted-foreground line-clamp-1">
            {result.address}, {result.city}
          </p>
        </div>

        <div className="text-right shrink-0">
          <div className="font-mono text-[20px] font-semibold tabular-nums text-foreground">
            {result.distance_km > 0 ? result.distance_km : "—"}
            <span className="text-[11px] font-normal text-muted-foreground ml-0.5">km</span>
          </div>
          <ConfidenceDot score={result.match_score} />
        </div>
      </div>

      {/* Why it matched */}
      <div className="mt-4 rounded-lg bg-surface-muted/50 border border-border/60 p-3 pt-2.5">
        <div className="flex items-center gap-1.5 mb-1.5">
          <FileText className="h-3 w-3 text-accent" />
          <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">AI Trace</span>
        </div>
        <p className="text-[12px] font-medium text-foreground leading-relaxed pl-4 border-l-[1.5px] border-accent/30">
          {result.matched_reason}
        </p>
      </div>

      {/* Trust Score Warning */}
      {result.trust_score < 0.8 && result.trust_flags?.length > 0 && (
        <div className="mt-2 rounded-lg bg-warning/5 border border-warning/20 p-3 pt-2.5">
          <div className="flex items-center gap-1.5 mb-1.5">
            <AlertCircle className="h-3 w-3 text-warning" />
            <span className="text-[10px] font-semibold uppercase tracking-wider text-warning/80">Data Warning</span>
          </div>
          <div className="pl-4 border-l-[1.5px] border-warning/30">
            {result.trust_flags.map((flag, i) => (
              <p key={i} className="text-[11.5px] font-medium text-warning/90 leading-relaxed">
                {flag}
              </p>
            ))}
          </div>
        </div>
      )}

      {/* Capabilities */}
      {result.matched_capabilities.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1">
          {result.matched_capabilities.slice(0, 6).map((c) => (
            <CapabilityChip key={c} capability={c} status="matched" />
          ))}
          {result.capabilities.filter((c) => !result.matched_capabilities.includes(c)).slice(0, 3).map((c) => (
            <CapabilityChip key={c} capability={c} status="available" />
          ))}
        </div>
      )}

      {/* Stats row */}
      <div className="mt-4 flex items-center gap-4 text-[12px] text-muted-foreground">
        <span className="inline-flex items-center gap-1">
          <BedDouble className="h-3.5 w-3.5" />
          <span className="text-foreground font-medium tabular-nums">{result.total_beds}</span> beds
        </span>
        {result.icu_beds > 0 && (
          <span className="inline-flex items-center gap-1">
            <span className="text-foreground font-medium tabular-nums">{result.icu_beds}</span> ICU
          </span>
        )}
        {result.accreditations.length > 0 && (
          <span className="inline-flex items-center gap-1">
            <ShieldCheck className="h-3.5 w-3.5" />
            {result.accreditations.join(" · ")}
          </span>
        )}
        <span className={cn(
          "ml-auto text-[10px] font-mono",
          result.data_age_days > 365 ? "text-warning" : "text-muted-foreground/60"
        )}>
          updated {result.data_age_days}d ago
        </span>
      </div>

      {/* Actions */}
      <div className="mt-4 flex items-center gap-2 pt-4 border-t border-border">
        <a
          href={`tel:${result.contact_phone}`}
          className="inline-flex items-center gap-1.5 rounded-md bg-primary text-primary-foreground px-3 py-1.5 text-[12px] font-medium hover:bg-primary/90 transition-colors"
        >
          <Phone className="h-3 w-3" /> Call
        </a>
        <a
          href={result.directions_url}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-[12px] font-medium text-foreground hover:bg-surface-muted transition-colors"
        >
          <Navigation className="h-3 w-3" /> Directions
        </a>
        <button
          onClick={toggleCompare}
          disabled={compareFull}
          className={cn(
            "inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-[12px] font-medium transition-colors",
            inCompare
              ? "border-accent/30 bg-accent-soft text-accent"
              : "border-border text-muted-foreground hover:bg-surface-muted disabled:opacity-40"
          )}
        >
          <GitCompare className="h-3 w-3" />
          {inCompare ? "Added" : "Compare"}
        </button>
        <ShareButton
          facilityName={result.facility_name}
          address={`${result.address}, ${result.city}`}
          phone={result.contact_phone || ""}
          directionsUrl={result.directions_url}
          facilityId={result.facility_id}
          className="ml-auto"
        />
      </div>
    </article>
  );
}