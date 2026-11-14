import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Database, RefreshCw, ServerCog } from "lucide-react";
import { api } from "../lib/api";
import { fmtDateTime, fmtNumber, timeAgo, titleCase } from "../lib/format";
import type { DataSource } from "../lib/types";
import { useSession } from "../store/session";
import { Card, CardHeader, EmptyState, ErrorState, Loading, StateBadge, StatusBadge, toast } from "../components/ui";
import { useFallbackPolling } from "../hooks/useLiveUpdates";

interface IngestionRun {
  id: number;
  source_id: string;
  status: string;
  records: number;
  message: string;
  started_at: string;
  finished_at: string | null;
  duration_ms: number | null;
}

export default function DataHealth() {
  const has = useSession((s) => s.has);
  const [filter, setFilter] = useState("");
  const queryClient = useQueryClient();
  const polling = useFallbackPolling(true);
  const query = useQuery({
    queryKey: ["data-sources"],
    queryFn: () => api<{ sources: DataSource[]; runs: IngestionRun[]; states: string[] }>("/api/v1/admin/data-sources"),
    ...polling,
  });

  const ingest = useMutation({
    mutationFn: (sourceId: string) => api(`/api/v1/admin/data-sources/${sourceId}/ingest`, { method: "POST" }),
    onSuccess: () => { toast("Ingestion run finished — check the run log.", "ok"); queryClient.invalidateQueries(); },
    onError: (error) => toast(error instanceof Error ? error.message : "Ingestion failed", "error"),
  });

  const sources = useMemo(() => {
    const rows = query.data?.sources ?? [];
    if (!filter) return rows;
    return rows.filter((source) => source.state === filter);
  }, [query.data, filter]);

  const counts = useMemo(() => {
    const map: Record<string, number> = {};
    for (const source of query.data?.sources ?? []) map[source.state] = (map[source.state] ?? 0) + 1;
    return map;
  }, [query.data]);

  const ingestable = new Set(["open-meteo-precip", "open-meteo-soil", "sim-rainfall"]);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Data Health</h1>
        <p className="text-sm text-muted">
          Every input carries a state, freshness SLA, licence and fallback. A source is only LIVE when it is genuinely
          connected and recent.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-2 md:grid-cols-6">
        {["LIVE", "STALE", "DEGRADED", "SIMULATED", "UNAVAILABLE", "CACHED"].map((state) => (
          <button key={state} className={`card px-3 py-2 text-left ${filter === state ? "border-forest" : ""}`} onClick={() => setFilter(filter === state ? "" : state)}>
            <div className="kpi-label">{state}</div>
            <div className="stat-value">{fmtNumber(counts[state] ?? 0)}</div>
          </button>
        ))}
      </div>

      {query.isLoading ? <Loading label="Loading source registry" /> : null}
      {query.error ? <ErrorState error={query.error} onRetry={() => query.refetch()} /> : null}

      <Card>
        <CardHeader title="Source registry" subtitle={`${sources.length} sources`} icon={<Database size={16} />} />
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr><th>Source</th><th>Category</th><th>State</th><th>Freshness</th><th>Resolution</th><th>Licence</th><th>Notes</th><th /></tr>
            </thead>
            <tbody>
              {sources.map((source) => (
                <tr key={source.id}>
                  <td>
                    <div className="font-medium">{source.name}</div>
                    <div className="text-2xs text-muted">{source.provider}</div>
                  </td>
                  <td className="text-muted">{source.category}</td>
                  <td><StateBadge state={source.state} /></td>
                  <td className="whitespace-nowrap text-2xs text-muted">
                    {source.last_success_at ? `ok ${timeAgo(source.last_success_at)}` : "never"}
                    <div>SLA {fmtNumber(source.freshness_sla_min / 60, 1)} h</div>
                  </td>
                  <td className="text-2xs text-muted">{source.spatial_resolution}<div>{source.temporal_resolution}</div></td>
                  <td className="max-w-[180px] text-2xs text-muted">{source.licence}</td>
                  <td className="max-w-[320px] text-2xs text-muted">{source.notes}{source.last_error ? <div className="text-critical">Last error: {source.last_error}</div> : null}</td>
                  <td>
                    {has("sources:write") && ingestable.has(source.id) ? (
                      <button className="btn btn-sm" disabled={ingest.isPending} onClick={() => ingest.mutate(source.id)}>
                        <RefreshCw size={12} className={ingest.isPending ? "animate-spin" : ""} /> Fetch
                      </button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!sources.length && !query.isLoading ? <EmptyState title="No sources in this state" /> : null}
      </Card>

      <Card>
        <CardHeader title="Ingestion history" subtitle="Retries use exponential backoff; failures are recorded, not hidden." icon={<ServerCog size={16} />} />
        <div className="table-wrap">
          <table className="data">
            <thead><tr><th>Source</th><th>Status</th><th>Records</th><th>Started</th><th>Duration</th><th>Message</th></tr></thead>
            <tbody>
              {(query.data?.runs ?? []).map((run) => (
                <tr key={run.id}>
                  <td className="mono">{run.source_id}</td>
                  <td><StatusBadge status={run.status} /></td>
                  <td className="numeric">{run.records}</td>
                  <td className="whitespace-nowrap text-muted">{fmtDateTime(run.started_at)}</td>
                  <td className="numeric text-muted">{run.duration_ms !== null ? `${run.duration_ms} ms` : "—"}</td>
                  <td className="max-w-[380px] text-2xs text-muted">{run.message || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!(query.data?.runs ?? []).length ? <EmptyState title="No ingestion runs yet" body="Run a live fetch to populate the registry." /> : null}
      </Card>

      <Card className="p-4">
        <div className="eyebrow">Attribution</div>
        <ul className="mt-1 space-y-1 text-2xs text-muted">
          {(query.data?.sources ?? []).filter((source) => ["LIVE", "SIMULATED"].includes(source.state)).map((source) => (
            <li key={source.id}>{source.attribution} — {titleCase(source.category)}</li>
          ))}
          <li>Basemap © OpenStreetMap contributors (ODbL).</li>
        </ul>
      </Card>
    </div>
  );
}
