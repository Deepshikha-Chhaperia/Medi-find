import { Link, useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { getFacility } from "@/lib/api";
import type { Facility } from "@/types/medifind";
import { CAPABILITY_META, CAPABILITY_CATEGORIES } from "@/data/capabilities";
import { CapabilityChip } from "@/components/medifind/CapabilityChip";
import { ConfidenceDot } from "@/components/medifind/ConfidenceDot";
import { MapView } from "@/components/medifind/MapView";
import { ArrowLeft, BedDouble, Phone, Navigation, Mail, Globe, Clock, ShieldCheck, FileText, Calendar } from "lucide-react";

export default function FacilityDetail() {
  const { id } = useParams();
  const [facility, setFacility] = useState<Facility | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    const run = async () => {
      if (!id) {
        setLoading(false);
        return;
      }
      const data = await getFacility(id);
      if (!mounted) return;
      setFacility(data);
      setLoading(false);
    };
    run();
    return () => {
      mounted = false;
    };
  }, [id]);

  const f = facility;

  if (loading) {
    return <div className="rounded-xl border border-border bg-surface p-12 text-center">Loading facility profile...</div>;
  }

  if (!f) {
    return (
      <div className="rounded-xl border border-border bg-surface p-12 text-center">
        <p className="text-foreground font-medium">Facility not found.</p>
        <Link to="/" className="mt-2 inline-block text-[13px] text-accent hover:underline">Back to search</Link>
      </div>
    );
  }

  const capsByCat = CAPABILITY_CATEGORIES.map(cat => ({
    cat,
    items: f.capabilities.filter(c => CAPABILITY_META[c]?.category === cat),
  })).filter(g => g.items.length > 0);

  return (
    <div className="space-y-6">
      <Link to="/results" className="inline-flex items-center gap-1.5 text-[12px] text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-3.5 w-3.5" /> Back to results
      </Link>

      {/* Header */}
      <div className="rounded-2xl border border-border bg-surface overflow-hidden">
        <div className="bg-gradient-hero p-6 sm:p-8 border-b border-border">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">{f.facility_type}</span>
                {f.emergency_24x7 && (
                  <span className="inline-flex items-center gap-1 rounded-md bg-emergency/10 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-emergency">
                    <Clock className="h-2.5 w-2.5" /> 24/7
                  </span>
                )}
                {(f.accreditations || []).map(a => (
                  <span key={a} className="inline-flex items-center gap-1 rounded-md border border-border px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
                    <ShieldCheck className="h-2.5 w-2.5" /> {a}
                  </span>
                ))}
              </div>
              <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight text-foreground text-balance">
                {f.facility_name}
              </h1>
              <p className="mt-2 text-[14px] text-muted-foreground">
                {[f.address, f.city, f.state, f.pin_code].filter(Boolean).join(", ")}
              </p>
              <div className="mt-3">
                <ConfidenceDot score={f.extraction_confidence} label="Extraction confidence" />
              </div>
            </div>
          </div>

          <div className="mt-6 flex flex-wrap items-center gap-2">
            <a href={`tel:${f.contact_phone || ""}`} className="inline-flex items-center gap-1.5 rounded-lg bg-primary text-primary-foreground px-3.5 py-2 text-[13px] font-medium hover:bg-primary/90">
              <Phone className="h-3.5 w-3.5" /> {f.contact_phone}
            </a>
            <a href={`https://www.google.com/maps/dir/?api=1&destination=${f.lat || 0},${f.lng || 0}`} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3.5 py-2 text-[13px] font-medium hover:bg-surface-muted">
              <Navigation className="h-3.5 w-3.5" /> Get directions
            </a>
            {f.contact_email && (
              <a href={`mailto:${f.contact_email}`} className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3.5 py-2 text-[13px] font-medium hover:bg-surface-muted">
                <Mail className="h-3.5 w-3.5" /> Email
              </a>
            )}
            {f.website && (
              <a href={f.website} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3.5 py-2 text-[13px] font-medium hover:bg-surface-muted">
                <Globe className="h-3.5 w-3.5" /> Website
              </a>
            )}
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 divide-x divide-border border-b border-border">
          {[
            { label: "Total beds", value: f.total_beds, icon: BedDouble },
            { label: "ICU beds", value: f.icu_beds, icon: BedDouble },
            { label: "NICU beds", value: f.nicu_beds ?? "—", icon: BedDouble },
            { label: "Hours", value: f.operational_hours, icon: Clock, small: true },
          ].map(({ label, value, icon: Icon, small }) => (
            <div key={label} className="p-4 sm:p-5">
              <div className="flex items-center gap-1.5 text-muted-foreground">
                <Icon className="h-3 w-3" />
                <span className="text-[10px] uppercase tracking-wider">{label}</span>
              </div>
              <div className={`mt-1 font-semibold tabular-nums text-foreground ${small ? "text-sm" : "text-2xl"}`}>
                {value}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Capabilities */}
        <div className="lg:col-span-2 space-y-6">
          <section className="rounded-xl border border-border bg-surface p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-[13px] font-semibold uppercase tracking-wider text-muted-foreground">Capabilities</h2>
              <span className="font-mono text-[11px] text-muted-foreground">{f.capabilities.length} verified</span>
            </div>
            <div className="space-y-4">
              {capsByCat.map(({ cat, items }) => (
                <div key={cat}>
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1.5">{cat}</p>
                  <div className="flex flex-wrap gap-1">
                    {items.map(c => <CapabilityChip key={c} capability={c} status="matched" size="md" />)}
                  </div>
                </div>
              ))}
            </div>
          </section>

          {f.equipment.length > 0 && (
            <section className="rounded-xl border border-border bg-surface p-5">
              <h2 className="text-[13px] font-semibold uppercase tracking-wider text-muted-foreground mb-3">Equipment</h2>
              <ul className="grid sm:grid-cols-2 gap-2">
                {f.equipment.map((e, i) => (
                  <li key={i} className="flex items-center gap-2 text-[13px] text-foreground">
                    <span className="h-1 w-1 rounded-full bg-accent" />
                    {e}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {/* Source */}
          <section className="rounded-xl border border-border bg-surface p-5">
            <h2 className="text-[13px] font-semibold uppercase tracking-wider text-muted-foreground mb-3">Source intelligence</h2>
            <div className="rounded-lg bg-surface-muted p-3 border border-border">
              <div className="flex items-center gap-2 text-[12px] text-muted-foreground mb-2">
                <FileText className="h-3.5 w-3.5" />
                <span className="font-mono">{f.source_doc}</span>
                <span className="ml-auto inline-flex items-center gap-1">
                  <Calendar className="h-3 w-3" /> {f.data_age_days}d old
                </span>
              </div>
              {f.source_excerpt && (
                <p className="text-[13px] text-foreground italic leading-relaxed">
                  "{f.source_excerpt}"
                </p>
              )}
            </div>
          </section>
        </div>

        {/* Map */}
        <div className="lg:sticky lg:top-20 h-[400px] lg:h-[500px]">
          <MapView
            results={[
              {
                ...f,
                rank: 1,
                distance_km: 0,
                match_score: f.extraction_confidence,
                match_confidence: f.extraction_confidence >= 0.75 ? "High" : f.extraction_confidence >= 0.5 ? "Medium" : "Low",
                matched_capabilities: f.capabilities,
                matched_reason: "Facility profile",
                directions_url: `https://www.google.com/maps/dir/?api=1&destination=${f.lat || 0},${f.lng || 0}`,
              },
            ]}
            center={f.lat && f.lng ? [f.lat, f.lng] : undefined}
            zoom={13}
          />
        </div>
      </div>
    </div>
  );
}