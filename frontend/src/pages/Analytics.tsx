import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Download, Info } from "lucide-react";
import { api, downloadFile } from "../lib/api";
import { fmtNumber, riskMeta, timeAgo } from "../lib/format";
import { useSession } from "../store/session";
import { Card, CardHeader, ErrorState, Loading, UncalibratedNote, toast } from "../components/ui";

interface AnalyticsPayload {
  jurisdiction: { districts: string[]; statewide: boolean };
  window_days: number;
  risk: {
    by_district: Array<{ district_name: string; zones: number; avg_hazard: number; critical: number; warning: number; watch: number; safe: number; population_exposed: number }>;
    by_level: Record<string, number>;
    by_priority: Record<string, number>;
    by_coverage: Record<string, number>;
  };
  rainfall: { series: Array<{ date: string; rainfall_24h_mean: number }> };
  incidents: { by_year: Array<{ year: number; count: number }>; total: number; verified: number; synthetic: number };
  alerts: { by_status: Record<string, number>; by_severity: Record<string, number>; delivery_status: Record<string, number>; approved: number; mean_approval_minutes: number | null };
  response: { total: number; by_status: Record<string, number>; mean_close_minutes: number | null; resolved: number };
  reports: { total: number; pending: number; verified: number; rejected: number; mean_verification_minutes: number | null };
  model: { version: string | null; status: string | null; validation_status: string; metrics: Record<string, unknown>; metrics_note: string; evaluated_at: string | null };
}

export default function Analytics() {
  const has = useSession((s) => s.has);
  const [exporting, setExporting] = useState(false);
  const query = useQuery({ queryKey: ["analytics"], queryFn: () => api<AnalyticsPayload>("/api/v1/analytics") });

  const exportData = async (dataset: "zones" | "alerts" | "reports", format: "csv" | "geojson") => {
    setExporting(true);
    try {
      await downloadFile(`/api/v1/analytics/export?dataset=${dataset}&format=${format}`, `bhushakti-${dataset}.${format}`);
      toast("Export started", "ok");
    } catch (error) {
      toast(error instanceof Error ? error.message : "Export failed", "error");
    } finally {
      setExporting(false);
    }
  };

  const data = query.data;
  const levels = data ? Object.entries(data.risk.by_level).map(([name, value]) => ({ name, value, color: riskMeta[name as keyof typeof riskMeta]?.dot ?? "#888" })) : [];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Analytics</h1>
          <p className="text-sm text-muted">Traceable operational metrics. Nothing here is extrapolated or invented.</p>
        </div>
        <div className="flex flex-wrap gap-1.5">
          <button className="btn btn-sm" disabled={!has("analytics:export") || exporting} onClick={() => exportData("zones", "csv")}><Download size={14} /> Units CSV</button>
          <button className="btn btn-sm" disabled={!has("analytics:export") || exporting} onClick={() => exportData("zones", "geojson")}><Download size={14} /> Units GeoJSON</button>
          <button className="btn btn-sm" disabled={!has("analytics:export") || exporting} onClick={() => exportData("alerts", "csv")}><Download size={14} /> Alerts CSV</button>
        </div>
      </div>

      {query.isLoading ? <Loading label="Loading analytics" /> : null}
      {query.error ? <ErrorState error={query.error} onRetry={() => query.refetch()} /> : null}

      {data ? (
        <>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {[
              { label: "Zones assessed", value: fmtNumber(Object.values(data.risk.by_level).reduce((a, b) => a + b, 0)) },
              { label: "Alerts approved", value: fmtNumber(data.alerts.approved), hint: `mean approval ${data.alerts.mean_approval_minutes ?? "—"} min` },
              { label: "Reports verified", value: fmtNumber(data.reports.verified), hint: `${data.reports.pending} pending` },
              { label: "Assignments resolved", value: fmtNumber(data.response.resolved), hint: `mean close ${data.response.mean_close_minutes ?? "—"} min` },
            ].map((kpi) => (
              <Card key={kpi.label} className="px-3 py-2.5">
                <div className="kpi-label">{kpi.label}</div>
                <div className="stat-value mt-1">{kpi.value}</div>
                {kpi.hint ? <div className="mt-1 text-2xs text-muted">{kpi.hint}</div> : null}
              </Card>
            ))}
          </div>

          <div className="grid gap-3 lg:grid-cols-2">
            <Card>
              <CardHeader title="Average hazard by district" subtitle="Prototype index (0–100); not a probability" />
              <div className="h-64 px-2 py-3">
                <ResponsiveContainer>
                  <BarChart data={data.risk.by_district}>
                    <CartesianGrid stroke="var(--line)" strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="district_name" tick={{ fontSize: 10 }} interval={0} />
                    <YAxis domain={[0, 100]} tick={{ fontSize: 10 }} width={28} />
                    <Tooltip contentStyle={{ fontSize: 12 }} />
                    <Bar dataKey="avg_hazard" name="Avg hazard index" fill="var(--forest)" radius={[3, 3, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>

            <Card>
              <CardHeader title="Hazard distribution" subtitle="Latest operational assessment per unit" />
              <div className="h-64 px-2 py-3">
                <ResponsiveContainer>
                  <PieChart>
                    <Pie data={levels} dataKey="value" nameKey="name" innerRadius={46} outerRadius={78} paddingAngle={2}>
                      {levels.map((entry) => <Cell key={entry.name} fill={entry.color} />)}
                    </Pie>
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <Tooltip contentStyle={{ fontSize: 12 }} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </Card>

            <Card>
              <CardHeader title="Rainfall trend" subtitle="District-centre model grid point, 24 h totals" />
              <div className="h-60 px-2 py-3">
                {data.rainfall.series.length ? (
                  <ResponsiveContainer>
                    <LineChart data={data.rainfall.series}>
                      <CartesianGrid stroke="var(--line)" strokeDasharray="3 3" vertical={false} />
                      <XAxis dataKey="date" tick={{ fontSize: 10 }} />
                      <YAxis tick={{ fontSize: 10 }} width={30} unit="mm" />
                      <Tooltip contentStyle={{ fontSize: 12 }} />
                      <Line type="monotone" dataKey="rainfall_24h_mean" stroke="var(--blue)" strokeWidth={1.8} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                ) : <p className="px-3 py-6 text-xs text-muted">No rainfall observations in this window.</p>}
              </div>
            </Card>

            <Card>
              <CardHeader title="Historical inventory" subtitle="Demo records are counted separately" />
              <div className="h-60 px-2 py-3">
                <ResponsiveContainer>
                  <BarChart data={data.incidents.by_year}>
                    <CartesianGrid stroke="var(--line)" strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="year" tick={{ fontSize: 10 }} />
                    <YAxis tick={{ fontSize: 10 }} width={24} allowDecimals={false} />
                    <Tooltip contentStyle={{ fontSize: 12 }} />
                    <Bar dataKey="count" name="Records" fill="var(--slate)" radius={[3, 3, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="border-t border-line px-3 py-2 text-2xs text-muted">
                {data.incidents.total} records · {data.incidents.verified} verified · {data.incidents.synthetic} synthetic demonstration records
              </div>
            </Card>
          </div>

          <div className="grid gap-3 lg:grid-cols-3">
            <Card className="p-3">
              <div className="eyebrow">Coverage distribution</div>
              <div className="mt-2 space-y-1 text-xs">
                {Object.entries(data.risk.by_coverage).map(([key, value]) => (
                  <div key={key} className="flex justify-between"><span className="text-muted">{key}</span><span className="numeric">{value}</span></div>
                ))}
              </div>
            </Card>
            <Card className="p-3">
              <div className="eyebrow">Priority distribution</div>
              <div className="mt-2 space-y-1 text-xs">
                {Object.entries(data.risk.by_priority).map(([key, value]) => (
                  <div key={key} className="flex justify-between"><span className="text-muted">{key}</span><span className="numeric">{value}</span></div>
                ))}
              </div>
            </Card>
            <Card className="p-3">
              <div className="eyebrow">Delivery status</div>
              <div className="mt-2 space-y-1 text-xs">
                {Object.entries(data.alerts.delivery_status).map(([key, value]) => (
                  <div key={key} className="flex justify-between"><span className="text-muted">{key.replaceAll("_", " ")}</span><span className="numeric">{value}</span></div>
                ))}
                {!Object.keys(data.alerts.delivery_status).length ? <p className="text-muted">No deliveries recorded.</p> : null}
              </div>
            </Card>
          </div>

          <Card className="p-4">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <div className="flex items-center gap-2 text-sm font-semibold"><Info size={15} /> Model validation</div>
                <div className="mt-1 text-xs text-muted">{data.model.metrics_note}</div>
              </div>
              <span className="badge border-watch/40 text-watch bg-watch/10">VALIDATION IN PROGRESS</span>
            </div>
            <div className="mt-2 grid gap-2 text-xs sm:grid-cols-3">
              <div><span className="kpi-label">Active model</span><div className="mono">{data.model.version}</div></div>
              <div><span className="kpi-label">Status</span><div>{data.model.status}</div></div>
              <div><span className="kpi-label">Last evaluation</span><div>{timeAgo(data.model.evaluated_at)}</div></div>
            </div>
            <div className="mt-3"><UncalibratedNote /></div>
          </Card>

          <details className="card p-3">
            <summary className="cursor-pointer text-xs font-semibold">Accessible data table (units by district)</summary>
            <div className="mt-2 overflow-x-auto">
              <table className="data">
                <thead><tr><th>District</th><th>Units</th><th>Avg hazard</th><th>Critical</th><th>Warning</th><th>Watch</th><th>Safe</th></tr></thead>
                <tbody>
                  {data.risk.by_district.map((row) => (
                    <tr key={row.district_name}>
                      <td>{row.district_name}</td><td className="numeric">{row.zones}</td><td className="numeric">{row.avg_hazard}</td>
                      <td className="numeric">{row.critical}</td><td className="numeric">{row.warning}</td><td className="numeric">{row.watch}</td><td className="numeric">{row.safe}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
        </>
      ) : null}
    </div>
  );
}
