import { useEffect, useState } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { Check, X, ArrowLeft, Phone, Navigation } from "lucide-react";
import { useSearchStore } from "@/store/useSearchStore";
import { getFacility } from "@/lib/api";
import type { Facility } from "@/types/medifind";
import { CAPABILITY_META, CAPABILITY_CATEGORIES } from "@/data/capabilities";

const ALL_CAPS = Object.keys(CAPABILITY_META);

export default function Compare() {
  const [params] = useSearchParams();
  const { clearCompare } = useSearchStore();
  const ids = (params.get("ids") || "").split(",").filter(Boolean).slice(0, 3);
  const [facilities, setFacilities] = useState<Facility[]>([]);

  useEffect(() => {
    const run = async () => {
      const rows = await Promise.all(ids.map((id) => getFacility(id)));
      setFacilities(rows.filter(Boolean) as Facility[]);
    };
    run();
  }, [params.toString()]);

  if (facilities.length < 2) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4 text-center px-4">
        <div className="text-5xl">Comparison</div>
        <h1 className="text-xl font-semibold">Add at least 2 facilities to compare</h1>
        <p className="text-muted-foreground text-sm">Use the Compare button on any facility card in search results.</p>
        <Link to="/results" className="rounded-lg bg-primary text-primary-foreground px-4 py-2 text-sm font-medium">
          Back to Results
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="flex items-center gap-4 mb-8">
        <Link to="/results" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4" />
          Back to results
        </Link>
        <h1 className="text-2xl font-semibold text-foreground">Facility Comparison</h1>
        <button onClick={clearCompare} className="ml-auto text-sm text-muted-foreground hover:text-foreground">
          Clear all
        </button>
      </div>

      <div className="grid gap-4 mb-8" style={{ gridTemplateColumns: `200px repeat(${facilities.length}, 1fr)` }}>
        <div />
        {facilities.map((f) => (
          <div key={f.facility_id} className="rounded-2xl border border-border/50 bg-surface shadow-soft-sm overflow-hidden flex flex-col text-center p-5">
            <span className="inline-block rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider mb-2 bg-accent/10 text-accent">
              {f.facility_type || "Facility"}
            </span>
            <h2 className="font-semibold text-foreground text-[16px] leading-snug mb-1">{f.facility_name}</h2>
            <p className="text-[12px] font-medium text-muted-foreground">{[f.city, f.state].filter(Boolean).join(", ")}</p>
            <div className="mt-auto pt-4 flex gap-2 w-full justify-center">
              <a href={`tel:${f.contact_phone || ""}`} className="flex-1 inline-flex items-center justify-center gap-1.5 rounded-lg bg-primary text-primary-foreground py-1.5 text-[12px] font-medium">
                <Phone className="h-3.5 w-3.5" /> Call
              </a>
              <a href={`https://www.google.com/maps/dir/?api=1&destination=${f.lat || 0},${f.lng || 0}`} target="_blank" rel="noreferrer" className="flex-1 inline-flex items-center justify-center gap-1.5 rounded-lg border border-border py-1.5 text-[12px] font-medium text-foreground hover:bg-surface-muted">
                <Navigation className="h-3.5 w-3.5" /> Maps
              </a>
            </div>
          </div>
        ))}
      </div>

      <div className="rounded-2xl border border-border/60 bg-surface shadow-soft flex flex-col overflow-hidden">
        {[
          { label: "Emergency 24/7", render: (f: Facility) => f.emergency_24x7 ? <Check className="h-4 w-4 text-success mx-auto" /> : <X className="h-4 w-4 text-muted-foreground mx-auto" /> },
          { label: "Total Beds", render: (f: Facility) => <span className="font-mono font-semibold">{f.total_beds || "-"}</span> },
          { label: "ICU Beds", render: (f: Facility) => <span className="font-mono">{f.icu_beds || "-"}</span> },
          { label: "NICU Beds", render: (f: Facility) => <span className="font-mono">{f.nicu_beds || "-"}</span> },
          { label: "Accreditations", render: (f: Facility) => <span className="text-[11px]">{(f.accreditations || []).join(", ") || "-"}</span> },
          { label: "Operating Hours", render: (f: Facility) => <span className="text-[11px]">{f.operational_hours || "-"}</span> },
          { label: "Confidence", render: (f: Facility) => <span className="text-[11px] font-mono">{Math.round((f.extraction_confidence || 0) * 100)}%</span> },
        ].map((row, ri) => (
          <div key={row.label} className={`grid items-center ${ri % 2 === 0 ? "bg-surface" : "bg-surface-muted"}`} style={{ gridTemplateColumns: `200px repeat(${facilities.length}, 1fr)` }}>
            <div className="px-4 py-3 text-[12px] font-medium text-muted-foreground border-r border-border">{row.label}</div>
            {facilities.map((f) => (
              <div key={f.facility_id} className="px-4 py-3 text-center text-sm border-r border-border last:border-0">{row.render(f)}</div>
            ))}
          </div>
        ))}

        {CAPABILITY_CATEGORIES.map((cat) => {
          const catCaps = ALL_CAPS.filter((c) => CAPABILITY_META[c]?.category === cat);
          const anyHas = facilities.some((f) => catCaps.some((c) => (f.capabilities || []).includes(c)));
          if (!catCaps.length || !anyHas) return null;

          return (
            <div key={cat}>
              <div className="grid bg-primary items-center" style={{ gridTemplateColumns: `200px repeat(${facilities.length}, 1fr)` }}>
                <div className="px-4 py-2 text-[11px] font-semibold uppercase tracking-wider text-primary-foreground/70 border-r border-white/10">{cat}</div>
                {facilities.map((f) => <div key={f.facility_id} className="border-r border-white/10 last:border-0" />)}
              </div>
              {catCaps.map((capId, ci) => (
                <div key={capId} className={`grid items-center ${ci % 2 === 0 ? "bg-surface" : "bg-surface-muted"}`} style={{ gridTemplateColumns: `200px repeat(${facilities.length}, 1fr)` }}>
                  <div className="px-4 py-2.5 text-[12px] text-foreground border-r border-border">{CAPABILITY_META[capId]?.label}</div>
                  {facilities.map((f) => (
                    <div key={f.facility_id} className="flex justify-center py-2.5 border-r border-border last:border-0">
                      {(f.capabilities || []).includes(capId)
                        ? <Check className="h-4 w-4 text-success" />
                        : <X className="h-4 w-4 text-muted-foreground/30" />}
                    </div>
                  ))}
                </div>
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
}
