import { useEffect, useMemo, useState } from "react";
import { getCapabilities, getCapabilityGaps, listFacilities } from "@/lib/api";
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip } from "recharts";
import { TrendingDown, MapPin, AlertTriangle } from "lucide-react";
import type { Facility } from "@/types/medifind";

export default function Insights() {
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [capabilities, setCapabilities] = useState<Record<string, { label: string; category: string }>>({});
  const [gaps, setGaps] = useState<Array<{ district: string; state: string; missing: string[] }>>([]);

  useEffect(() => {
    const run = async () => {
      const [facs, caps, gapRes] = await Promise.all([
        listFacilities({ limit: 300 }),
        getCapabilities(),
        getCapabilityGaps(),
      ]);
      setFacilities(facs);
      setCapabilities(caps);
      setGaps(gapRes.gaps || []);
    };
    run();
  }, []);

  const capCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const f of facilities) {
      for (const c of f.capabilities || []) {
        counts[c] = (counts[c] || 0) + 1;
      }
    }
    return Object.entries(counts)
      .map(([cap, count]) => ({ cap, label: capabilities[cap]?.label || cap, count }))
      .sort((a, b) => a.count - b.count);
  }, [facilities, capabilities]);

  const rarest = capCounts.slice(0, 8);
  const districts = [...new Set(gaps.map((g) => `${g.district}, ${g.state}`))].length;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-serif tracking-tight text-foreground">Capability Insights</h1>
        <p className="text-[13.5px] font-sans text-muted-foreground mt-1">
          Real coverage and gap analysis from indexed facilities.
        </p>
      </div>

      <div className="grid gap-px rounded-xl border border-border bg-border overflow-hidden sm:grid-cols-4 shadow-sm">
        {[
          { l: "Facilities", v: facilities.length },
          { l: "Capabilities observed", v: capCounts.length },
          { l: "Districts with gaps", v: districts },
          { l: "Total gap flags", v: gaps.reduce((a, g) => a + g.missing.length, 0) },
        ].map(({ l, v }) => (
          <div key={l} className="bg-surface p-5">
            <p className="text-[11px] font-sans uppercase tracking-wider text-muted-foreground">{l}</p>
            <p className="mt-2 font-sans font-semibold tabular-nums text-foreground text-3xl">{v}</p>
          </div>
        ))}
      </div>

      <section className="rounded-xl border border-border bg-surface p-5 shadow-sm">
        <h2 className="text-[13px] font-sans font-semibold uppercase tracking-wider text-muted-foreground inline-flex items-center gap-2 mb-4">
          <TrendingDown className="h-4 w-4" /> Rarest capabilities
        </h2>
        <div className="h-72">
          <ResponsiveContainer>
            <BarChart data={rarest} layout="vertical" margin={{ left: 10, right: 20 }}>
              <XAxis type="number" hide />
              <YAxis dataKey="label" type="category" width={170} tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip />
              <Bar dataKey="count" radius={[0, 4, 4, 0]} fill="hsl(var(--destructive))" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="rounded-xl border border-accent/20 bg-accent/5 p-6 shadow-sm">
        <div className="flex items-start gap-3">
          <AlertTriangle className="h-5 w-5 text-accent shrink-0 mt-0.5" />
          <div className="flex-1">
            <h2 className="text-[14px] font-sans font-semibold text-foreground">Critical capability gaps by district</h2>
            <p className="text-[13px] font-sans text-muted-foreground mt-1 mb-4">
              Districts with missing capabilities in the current indexed dataset.
            </p>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {gaps.slice(0, 18).map((g) => (
                <div key={`${g.district}-${g.state}`} className="rounded-lg bg-surface border border-border p-3.5 shadow-sm">
                  <p className="text-[13px] font-semibold text-foreground mb-2.5 inline-flex items-center gap-1">
                    <MapPin className="h-3.5 w-3.5 text-muted-foreground" />
                    {g.district}, {g.state}
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {g.missing.slice(0, 6).map((id) => (
                      <span key={id} className="inline-flex items-center rounded border border-destructive/20 bg-destructive/5 px-1.5 py-0.5 text-[11px] font-medium text-destructive">
                        {capabilities[id]?.label || id}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
