import { useEffect, useState } from "react";
import { Upload, FileText, CheckCircle2, Loader2, AlertCircle, Database } from "lucide-react";
import { cn } from "@/lib/utils";
import { getIngestStatus, getIngestSources, getStats, ingestFiles, ingestGoogleSheet, listFacilities } from "@/lib/api";
import type { Facility } from "@/types/medifind";

const HACKATHON_SHEET_URL = "https://docs.google.com/spreadsheets/d/1ZDuDmoQlyxZIEahDBlrMjf2wiWG7xU81/edit?gid=1028775758#gid=1028775758";

export default function Admin() {
  const [stats, setStats] = useState<Record<string, unknown>>({});
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<Record<string, unknown> | null>(null);
  const [uploading, setUploading] = useState(false);
  const [sheetLoading, setSheetLoading] = useState(false);
  const [sources, setSources] = useState<Array<Record<string, unknown>>>([]);
  const [ingestError, setIngestError] = useState<string | null>(null);
  const [sheetUrl, setSheetUrl] = useState(HACKATHON_SHEET_URL);
  const [sheetGid, setSheetGid] = useState("1028775758");

  useEffect(() => {
    const run = async () => {
      try {
        const [s, facs, src] = await Promise.all([getStats(), listFacilities({ limit: 100 }), getIngestSources(10)]);
        setStats(s);
        setFacilities(facs);
        setSources(src.sources as Array<Record<string, unknown>>);
      } catch (err: unknown) {
        setIngestError(err instanceof Error ? err.message : "Backend unavailable. Check API and database configuration.");
      }
    };
    run();
  }, []);

  useEffect(() => {
    if (!jobId) return;
    const timer = setInterval(async () => {
      const s = await getIngestStatus(jobId);
      setJobStatus(s);
      if (s.status !== "RUNNING") {
        clearInterval(timer);
        const [newStats, facs, src] = await Promise.all([getStats(), listFacilities({ limit: 100 }), getIngestSources(10)]);
        setStats(newStats);
        setFacilities(facs);
        setSources(src.sources as Array<Record<string, unknown>>);
      }
    }, 2000);
    return () => clearInterval(timer);
  }, [jobId]);

  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setUploading(true);
    setIngestError(null);
    try {
      const result = await ingestFiles(Array.from(files));
      setJobId(result.job_id);
    } catch (err: unknown) {
      setIngestError(err instanceof Error ? err.message : "File ingestion failed");
    } finally {
      setUploading(false);
    }
  };

  const handleGoogleSheetIngest = async () => {
    setSheetLoading(true);
    setIngestError(null);
    try {
      const result = await ingestGoogleSheet({ sheet_url: sheetUrl.trim(), gid: sheetGid.trim() });
      setJobId(result.job_id);
      if (result.status !== "RUNNING") {
        setJobStatus({
          job_id: result.job_id,
          status: result.status,
          total_files: result.total_rows,
          processed_files: result.completed_rows ?? 0,
          failed_files: result.failed_rows ?? 0,
          pct_complete: 100,
        });
        const [newStats, facs, src] = await Promise.all([getStats(), listFacilities({ limit: 100 }), getIngestSources(10)]);
        setStats(newStats);
        setFacilities(facs);
        setSources(src.sources as Array<Record<string, unknown>>);
      }
    } catch (err: unknown) {
      setIngestError(err instanceof Error ? err.message : "Google Sheet ingestion failed");
    } finally {
      setSheetLoading(false);
    }
  };

  const totalDocs = Number(stats.total_documents || 0);
  const totalFacilities = Number(stats.total_facilities || 0);
  const totalCaps = Number(stats.total_capabilities_indexed || 0);
  const avgConf = Math.round(Number(stats.avg_extraction_confidence || 0) * 100);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Ingestion Console</h1>
        <p className="text-[13px] text-muted-foreground mt-1">
          Upload facility reports and monitor real ingestion progress from the backend pipeline.
        </p>
      </div>

      <div className="grid gap-px rounded-xl border border-border bg-border overflow-hidden sm:grid-cols-4">
        {[
          { l: "Documents", v: totalDocs },
          { l: "Facilities", v: totalFacilities },
          { l: "Capabilities", v: totalCaps },
          { l: "Avg confidence", v: `${avgConf}%` },
        ].map(({ l, v }) => (
          <div key={l} className="bg-surface p-4">
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground">{l}</p>
            <p className="mt-1 text-2xl font-semibold tabular-nums">{v}</p>
          </div>
        ))}
      </div>

      {ingestError && (
        <div className="rounded-xl border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {ingestError}
        </div>
      )}

      <label className="block cursor-pointer">
        <input
          type="file"
          multiple
          accept=".pdf,.csv,.txt,.xlsx,.html,.docx"
          className="sr-only"
          onChange={(e) => handleFiles(e.target.files)}
        />
        <div className="rounded-xl border-2 border-dashed border-border bg-surface p-12 text-center hover:border-accent/40 hover:bg-accent-soft/30 transition-colors">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-accent-soft text-accent mb-3">
            <Upload className="h-5 w-5" />
          </div>
          <p className="text-[14px] font-medium text-foreground">Drop facility reports or click to upload</p>
          <p className="mt-1 text-[12px] text-muted-foreground">PDF, CSV, XLSX, DOCX, HTML, TXT</p>
          {uploading && <p className="mt-2 text-[12px] text-accent">Uploading...</p>}
        </div>
      </label>

      <div className="rounded-xl border border-border bg-surface p-5">
        <div className="flex flex-col gap-4">
          <div>
            <h2 className="text-[13px] font-semibold uppercase tracking-wider text-muted-foreground">Google Sheet Source</h2>
            <p className="text-[12px] text-muted-foreground mt-1">
              Use the editable sheet URL and gid below. In fallback mode this refreshes directly from the public Google Sheet without requiring Neon.
            </p>
          </div>
          <div className="grid gap-3 md:grid-cols-[1fr_180px_auto]">
            <input
              value={sheetUrl}
              onChange={(e) => setSheetUrl(e.target.value)}
              placeholder="Google Sheet URL"
              className="h-10 rounded-md border border-border bg-background px-3 text-sm"
            />
            <input
              value={sheetGid}
              onChange={(e) => setSheetGid(e.target.value)}
              placeholder="gid"
              className="h-10 rounded-md border border-border bg-background px-3 text-sm"
            />
            <button
              onClick={handleGoogleSheetIngest}
              disabled={sheetLoading || !sheetUrl.trim() || !sheetGid.trim()}
              className="inline-flex items-center justify-center rounded-md bg-primary text-primary-foreground px-4 py-2 text-sm font-medium disabled:opacity-60"
            >
              {sheetLoading ? "Ingesting..." : "Ingest From Google Sheet"}
            </button>
          </div>
        </div>
      </div>

      {jobStatus && (
        <div className="rounded-xl border border-border bg-surface overflow-hidden">
          <div className="px-4 py-3 border-b border-border flex items-center justify-between">
            <h2 className="text-[13px] font-semibold uppercase tracking-wider text-muted-foreground">Ingestion Job</h2>
            <span className="font-mono text-[11px] text-muted-foreground">{String(jobStatus.status || "UNKNOWN")}</span>
          </div>
          <div className="p-4 space-y-2 text-sm">
            <p>Total files: {Number(jobStatus.total_files || 0)}</p>
            <p>Processed: {Number(jobStatus.processed_files || 0)}</p>
            <p>Failed: {Number(jobStatus.failed_files || 0)}</p>
            <div className="h-1 rounded-full bg-surface-muted overflow-hidden">
              <div className="h-full bg-accent" style={{ width: `${Number(jobStatus.pct_complete || 0)}%` }} />
            </div>
          </div>
        </div>
      )}

      <div className="rounded-xl border border-border bg-surface overflow-hidden">
        <div className="px-4 py-3 border-b border-border flex items-center justify-between">
          <h2 className="text-[13px] font-semibold uppercase tracking-wider text-muted-foreground">Source Provenance</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-border text-muted-foreground">
              <tr>
                <th className="px-4 py-2">Type</th>
                <th className="px-4 py-2">Rows</th>
                <th className="px-4 py-2">Status</th>
                <th className="px-4 py-2">Source URL</th>
              </tr>
            </thead>
            <tbody>
              {sources.map((s, idx) => (
                <tr key={idx} className="border-b border-border/60">
                  <td className="px-4 py-2">{String(s.source_type || "-")}</td>
                  <td className="px-4 py-2">
                    {Number(s.rows_inserted || 0)} / {Number(s.rows_fetched || 0)}
                  </td>
                  <td className="px-4 py-2">{String(s.status || "-")}</td>
                  <td className="px-4 py-2 max-w-[520px] truncate">{String(s.source_url || "-")}</td>
                </tr>
              ))}
              {!sources.length && (
                <tr>
                  <td className="px-4 py-6 text-muted-foreground" colSpan={4}>No source provenance records yet.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="rounded-xl border border-border bg-surface overflow-hidden">
          <div className="px-4 py-3 border-b border-border flex items-center justify-between">
            <h2 className="text-[13px] font-semibold uppercase tracking-wider text-muted-foreground inline-flex items-center gap-2">
              <Database className="h-3.5 w-3.5" /> Loaded facilities sample
            </h2>
            <span className="text-[11px] text-muted-foreground">showing first {facilities.length}</span>
          </div>
        <ul className="divide-y divide-border max-h-96 overflow-y-auto">
          {facilities.map((f) => (
            <li key={f.facility_id} className="px-4 py-2.5 grid grid-cols-[1fr,auto,auto,auto] items-center gap-3">
              <span className="text-[13px] font-medium text-foreground truncate">{f.facility_name}</span>
              <span className="text-[11px] text-muted-foreground font-mono truncate hidden sm:block">{f.source_doc || "-"}</span>
              <span className="text-[11px] tabular-nums text-muted-foreground">{(f.capabilities || []).length} caps</span>
              <span className={cn("text-[11px] tabular-nums w-12 text-right", (f.extraction_confidence || 0) >= 0.6 ? "text-success" : "text-warning")}>
                {Math.round((f.extraction_confidence || 0) * 100)}%
              </span>
            </li>
          ))}
          {!facilities.length && (
            <li className="px-4 py-8 text-center text-sm text-muted-foreground">No indexed facilities yet.</li>
          )}
        </ul>
      </div>
    </div>
  );
}
