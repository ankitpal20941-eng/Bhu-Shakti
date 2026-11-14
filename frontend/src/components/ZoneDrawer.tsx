import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { CheckCircle2, FileWarning, XCircle } from "lucide-react";
import clsx from "clsx";
import { api } from "../lib/api";
import { fmtDateTime, fmtNumber, riskMeta, timeAgo, titleCase } from "../lib/format";
import type { ZoneDetail } from "../lib/types";
import { useSession } from "../store/session";
import {
  CoverageBadge, Drawer, EmptyState, ErrorState, FieldNote, Loading, PriorityBadge, ReasonDialog,
  RiskBadge, StateBadge, StatusBadge, Tabs, UncalibratedNote, toast,
} from "./ui";
import { Badge, Separator } from "./shadcn";

type Tab = "overview" | "drivers" | "weather" | "exposure" | "history" | "reports" | "audit";

const TABS: Array<{ id: Tab; label: string }> = [
  { id: "overview", label: "Overview" },
  { id: "drivers", label: "Risk drivers" },
  { id: "weather", label: "Weather" },
  { id: "exposure", label: "Exposure" },
  { id: "history", label: "History" },
  { id: "reports", label: "Reports" },
  { id: "audit", label: "Audit" },
];

export function ZoneDrawer({ zoneId, onClose }: { zoneId: number | null; onClose: () => void }) {
  const [tab, setTab] = useState<Tab>("overview");
  const [verifyTarget, setVerifyTarget] = useState<{ id: number; decision: "VERIFIED" | "REJECTED" } | null>(null);
  const has = useSession((s) => s.has);
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ["zone", zoneId],
    queryFn: () => api<ZoneDetail>(`/api/v1/risk-zones/${zoneId}`),
    enabled: zoneId !== null,
  });

  const audit = useQuery({
    queryKey: ["zone-audit", zoneId],
    queryFn: () => api<{ entries: Array<{ id: number; at: string; actor: string; action: string; reason: string; entity: string }> }>(
      "/api/v1/admin/audit-logs?limit=200",
    ),
    enabled: zoneId !== null && tab === "audit" && has("audit:read"),
  });

  const verify = useMutation({
    mutationFn: ({ id, decision, note }: { id: number; decision: "VERIFIED" | "REJECTED"; note: string }) =>
      api(`/api/v1/reports/${id}/verify`, { method: "PATCH", json: { decision, note } }),
    onSuccess: (_data, variables) => {
      toast(`Report ${variables.decision === "VERIFIED" ? "verified — bounded risk adjustment applied" : "rejected"}`, "ok");
      queryClient.invalidateQueries();
    },
    onError: (error) => toast(error instanceof Error ? error.message : "Verification failed", "error"),
  });

  const detail = query.data;
  const history = useMemo(() => (detail?.history ?? []).map((row) => ({
    time: new Date(row.computed_at).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" }),
    hazard: row.hazard_index,
    label: row.hazard_level,
  })), [detail?.history]);

  const auditEntries = useMemo(() => {
    if (!audit.data || !detail) return [];
    return audit.data.entries.filter((entry) =>
      entry.entity === "zone" && String(detail.id) === String(entry.reason)
      || entry.reason.includes(detail.code)
      || (entry.entity === "report" && detail.reports.some((report) => String(report.id) === entry.reason))
      || (entry.entity === "alert" && detail.open_alerts.some((alert) => String(alert.id) === entry.reason))
    );
  }, [audit.data, detail]);

  return (
    <>
    <Drawer
      open={zoneId !== null}
      onClose={onClose}
      title={detail ? detail.name : "Risk unit"}
      subtitle={detail ? `${detail.district_name}, ${detail.state} · ${detail.code} · ${fmtNumber(detail.area_km2, 1)} km²` : "Loading unit…"}
      footer={detail ? (
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-1.5">
            <CoverageBadge level={detail.coverage_level} />
            <StateBadge state={detail.weather_source_state} />
          </div>
          <div className="text-2xs text-muted">Updated {timeAgo(detail.computed_at)} · {detail.model_version}</div>
        </div>
      ) : undefined}
    >
      {query.isLoading ? <Loading label="Loading unit intelligence" /> : null}
      {query.error ? <div className="p-4"><ErrorState error={query.error} onRetry={() => query.refetch()} /></div> : null}
      {detail ? (
        <>
          <div className="border-b border-line px-4 py-3">
            <div className="flex flex-wrap items-center gap-2">
              <RiskBadge level={detail.hazard_level} index={detail.hazard_index} size="lg" />
              <PriorityBadge level={detail.priority_level} showLabel />
              <span className="chip">{detail.probability_status.replace("_", " ")}</span>
              {detail.out_of_domain ? (
                <Badge variant="destructive" className="font-mono text-[9px] uppercase">
                  OUT OF DOMAIN
                </Badge>
              ) : null}
            </div>
            <Separator className="my-2.5" />
            <div className="mt-2 grid grid-cols-3 gap-2 text-center">
              <div className="rounded-lg border border-line bg-canvas px-2 py-1.5">
                <div className="kpi-label">Hazard</div>
                <div className="stat-value text-xl">{fmtNumber(detail.hazard_index, 0)}</div>
              </div>
              <div className="rounded-lg border border-line bg-canvas px-2 py-1.5">
                <div className="kpi-label">Exposure</div>
                <div className="stat-value text-xl">{fmtNumber(detail.exposure_score, 0)}</div>
              </div>
              <div className="rounded-lg border border-line bg-canvas px-2 py-1.5">
                <div className="kpi-label">Priority</div>
                <div className="stat-value text-xl">{detail.priority_level ?? "—"}</div>
              </div>
            </div>
          </div>

          <Tabs tabs={TABS} active={tab} onChange={setTab} />

          <div className="px-4 py-3">
            {tab === "overview" ? (
              <div className="space-y-4">
                <div>
                  <div className="eyebrow">Recommended action</div>
                  <p className="mt-1 rounded-lg border border-line bg-surface-2 px-3 py-2 text-sm">{detail.recommended_action ?? "No action recorded."}</p>
                </div>
                <UncalibratedNote />
                <div className="grid grid-cols-2 gap-3">
                  <FieldNote label="Vulnerability" value={fmtNumber(detail.vulnerability_score, 0)} hint={detail.vulnerability?.note} />
                  <FieldNote label="Confidence" value={detail.coverage_level ?? "—"} hint={detail.coverage?.method} />
                  <FieldNote label="Rainfall 24 h" value={`${fmtNumber(detail.inputs.rainfall?.["24h"], 1)} mm`} hint={`Observed ${timeAgo(detail.inputs.observed_at)}`} />
                  <FieldNote label="Soil moisture" value={`${fmtNumber(detail.inputs.soil_moisture_pct, 1)}%`} hint="0–7 cm layer" />
                </div>
                {history.length > 1 ? (
                  <div>
                    <div className="eyebrow mb-1">Hazard history (this build)</div>
                    <div className="h-28 w-full">
                      <ResponsiveContainer>
                        <AreaChart data={history}>
                          <CartesianGrid stroke="var(--line)" strokeDasharray="3 3" vertical={false} />
                          <XAxis dataKey="time" hide />
                          <YAxis domain={[0, 100]} width={24} tick={{ fontSize: 10 }} />
                          <Tooltip contentStyle={{ fontSize: 12 }} />
                          <Area type="monotone" dataKey="hazard" stroke="var(--forest)" fill="var(--forest-soft)" strokeWidth={1.6} />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                ) : null}
                {detail.trajectory?.points?.length ? (
                  <div>
                    <div className="eyebrow mb-1">Forecast trajectory (hazard index)</div>
                    <div className="h-32 w-full">
                      <ResponsiveContainer>
                        <BarChart data={detail.trajectory.points}>
                          <CartesianGrid stroke="var(--line)" strokeDasharray="3 3" vertical={false} />
                          <XAxis dataKey="horizon_h" tickFormatter={(v) => `${v}h`} tick={{ fontSize: 10 }} />
                          <YAxis domain={[0, 100]} width={24} tick={{ fontSize: 10 }} />
                          <Tooltip contentStyle={{ fontSize: 12 }} labelFormatter={(v) => `${v} h horizon`} />
                          <Bar dataKey="hazard_index" radius={[3, 3, 0, 0]}>
                            {detail.trajectory.points.map((point) => (
                              <Cell key={point.horizon_h} fill={riskMeta[point.hazard_level].dot} />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                    <p className="hint mt-1">{detail.trajectory.method} Unavailable: {detail.trajectory.unavailable_horizons.length ? detail.trajectory.unavailable_horizons.map((h) => `${h}h`).join(", ") : "none"}.</p>
                  </div>
                ) : null}
              </div>
            ) : null}

            {tab === "drivers" ? (
              <div className="space-y-4">
                <p className="text-sm">{detail.drivers.narrative}</p>
                <div>
                  <div className="eyebrow mb-1.5">Signed contributions to the hazard index</div>
                  <div className="space-y-1.5">
                    {detail.drivers.contributions.map((driver) => {
                      const width = Math.min(100, Math.abs(driver.index_effect) * 3.2);
                      const positive = driver.direction === "increases";
                      return (
                        <div key={driver.key} className="grid grid-cols-[1fr_auto] items-center gap-2">
                          <div>
                            <div className="flex items-center justify-between text-xs">
                              <span>{driver.label}</span>
                              <span className={clsx("numeric", positive ? "text-critical" : "text-safe")}>
                                {positive ? "+" : ""}{fmtNumber(driver.index_effect, 1)}
                              </span>
                            </div>
                            <div className="mt-0.5 h-2 rounded bg-surface-2">
                              <div className={clsx("h-2 rounded", positive ? "bg-critical/60" : "bg-safe/60")} style={{ width: `${width}%` }} />
                            </div>
                            {driver.provenance ? <div className="hint mt-0.5">{driver.provenance}</div> : null}
                          </div>
                          <span className="numeric w-14 text-right text-2xs text-muted">{driver.value ?? "—"}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
                <div className="rounded-lg border border-line bg-surface-2 p-3 text-xs">
                  <div className="font-semibold">Attribution method</div>
                  <p className="mt-1 text-muted">{detail.drivers.attribution_method}</p>
                  <p className="mt-2 text-muted">{detail.drivers.model_note}</p>
                </div>
                {detail.inputs.field_evidence ? (
                  <div className="rounded-lg border border-line p-3 text-xs">
                    <div className="font-semibold">Verified field evidence</div>
                    <p className="mt-1 text-muted">{detail.inputs.field_evidence.note}</p>
                    <p className="mt-1 numeric">Applied: +{fmtNumber(detail.inputs.field_evidence.applied_points, 1)} points (cap {detail.inputs.field_evidence.cap_points})</p>
                  </div>
                ) : null}
              </div>
            ) : null}

            {tab === "weather" ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  {["1h", "6h", "24h", "72h"].map((window) => (
                    <FieldNote key={window} label={`Rainfall ${window}`} value={`${fmtNumber(detail.inputs.rainfall?.[window], 1)} mm`} />
                  ))}
                  <FieldNote label="Soil moisture (0–7 cm)" value={`${fmtNumber(detail.inputs.soil_moisture_pct, 1)}%`} />
                  <FieldNote label="Observation" value={fmtDateTime(detail.inputs.observed_at)} hint={detail.inputs.weather_source_id ?? "No source"} />
                </div>
                <div className="flex items-center gap-2">
                  <StateBadge state={detail.inputs.weather_source_state} />
                  <span className="text-2xs text-muted">Threshold ratios vs intensity–duration envelope</span>
                </div>
                <div className="overflow-x-auto rounded-lg border border-line">
                  <table className="data">
                    <thead><tr><th>Window</th><th>Ratio</th><th>Threshold mm/h</th></tr></thead>
                    <tbody>
                      {Object.entries(detail.inputs.trigger?.ratios ?? {}).map(([key, value]) => (
                        <tr key={key}>
                          <td className="capitalize">{key.replace("r_", "").replace("fc", "forecast ")}</td>
                          <td className="numeric">{fmtNumber(value, 2)}</td>
                          <td className="numeric text-muted">{fmtNumber(detail.inputs.trigger?.thresholds_mm_per_h?.[key.replace("r_fc24", "24").replace("r_", "").replace("h", "h")] ?? null, 2)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <p className="hint">{detail.inputs.trigger?.id_source}</p>
                <div>
                  <div className="eyebrow mb-1">Forecast inputs</div>
                  {detail.trajectory?.forecast_observations?.length ? (
                    <div className="flex flex-wrap gap-1.5">
                      {detail.trajectory.forecast_observations.map((f) => (
                        <span key={f.horizon_h} className="chip">{f.horizon_h}h · {fmtNumber(f.rainfall_mm, 1)} mm</span>
                      ))}
                    </div>
                  ) : <p className="text-xs text-muted">No forecast ingested; trajectory is intentionally blank.</p>}
                  <p className="hint mt-1">Issued {fmtDateTime(detail.inputs.forecast_issued_at)}</p>
                </div>
              </div>
            ) : null}

            {tab === "exposure" ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  <FieldNote label="Exposure index" value={fmtNumber(detail.exposure?.score, 0)} hint={detail.exposure?.method} />
                  <FieldNote label="Est. population exposed" value={fmtNumber(detail.exposure?.population_exposed)} hint="Dataset estimate — not a census" />
                  <FieldNote label="Road length at risk" value={`${fmtNumber(detail.exposure?.road_km_at_risk, 1)} km`} />
                  <FieldNote label="Vulnerability" value={fmtNumber(detail.vulnerability?.score, 0)} hint={detail.vulnerability?.note} />
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {Object.entries(detail.exposure?.counts ?? {}).map(([kind, count]) => (
                    <span key={kind} className="chip">{titleCase(kind)}: {count}</span>
                  ))}
                </div>
                <div className="rounded-lg border border-line">
                  <table className="data">
                    <thead><tr><th>Asset</th><th>Type</th><th>Distance</th></tr></thead>
                    <tbody>
                      {(detail.exposure?.assets ?? []).map((asset) => (
                        <tr key={`${asset.id}-${asset.name}`}>
                          <td>{asset.name}</td>
                          <td className="capitalize text-muted">{asset.kind}</td>
                          <td className="numeric">{fmtNumber(asset.distance_km, 1)} km</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {!detail.exposure?.assets?.length ? <EmptyState title="No exposed assets in the buffer" body="The exposure engine found no assets inside this unit or its 2.5 km buffer." /> : null}
                </div>
                <div className="rounded-lg border border-line bg-surface-2 p-3 text-xs">
                  <div className="font-semibold">Priority composition</div>
                  <p className="mt-1 text-muted">{detail.priority?.formula}</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {Object.entries(detail.priority?.contributions ?? {}).map(([key, value]) => (
                      <span key={key} className="chip">{titleCase(key)}: {fmtNumber(value, 1)}</span>
                    ))}
                  </div>
                  <p className="mt-2 text-muted">{detail.priority?.note}</p>
                </div>
                <p className="hint">{detail.exposure?.notes?.join(" ")}</p>
              </div>
            ) : null}

            {tab === "history" ? (
              <div className="space-y-4">
                <div>
                  <div className="eyebrow mb-1">Historical landslides within 8 km</div>
                  <div className="space-y-1.5">
                    {detail.incidents.map((incident) => (
                      <div key={incident.id} className="rounded-lg border border-line px-3 py-2 text-xs">
                        <div className="flex items-center justify-between">
                          <span className="font-medium">{incident.occurred_on}</span>
                          <span className="chip">{incident.verified ? "verified" : "unverified"}</span>
                        </div>
                        <div className="mt-0.5 text-muted">{incident.distance_km} km away · ±{incident.location_accuracy_m} m · ±{incident.date_uncertainty_days} d</div>
                        <div className="mt-1 text-2xs text-muted">{incident.source}</div>
                      </div>
                    ))}
                    {!detail.incidents.length ? <p className="text-xs text-muted">No records in the demo inventory for this radius.</p> : null}
                  </div>
                </div>
                <div>
                  <div className="eyebrow mb-1">Assessment history</div>
                  <div className="max-h-56 overflow-y-auto rounded-lg border border-line">
                    <table className="data">
                      <thead><tr><th>Computed</th><th>Hazard</th><th>Level</th><th>Priority</th></tr></thead>
                      <tbody>
                        {[...detail.history].reverse().map((row) => (
                          <tr key={row.computed_at}>
                            <td className="whitespace-nowrap text-muted">{fmtDateTime(row.computed_at)}</td>
                            <td className="numeric">{fmtNumber(row.hazard_index, 1)}</td>
                            <td><RiskBadge level={row.hazard_level} /></td>
                            <td><PriorityBadge level={row.priority_level} /></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            ) : null}

            {tab === "reports" ? (
              <div className="space-y-3">
                {detail.reports.map((report) => (
                  <div key={report.id} className="rounded-lg border border-line px-3 py-2 text-xs">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="font-medium">{titleCase(report.hazard_type)}</span>
                      <StatusBadge status={report.status} />
                    </div>
                    <p className="mt-1 text-muted">{report.description || "No description"}</p>
                    <div className="mt-1 flex flex-wrap gap-2 text-2xs text-muted">
                      <span>{fmtDateTime(report.observed_at)}</span>
                      <span>{report.media_count} media</span>
                      <span>{report.sync_source}</span>
                      {report.risk_adjustment_applied ? <span>+{fmtNumber(report.risk_adjustment_applied, 1)} hazard points</span> : null}
                    </div>
                    {report.status === "PENDING_VERIFICATION" && has("reports:verify") ? (
                      <div className="mt-2 flex gap-2">
                        <button className="btn btn-sm" onClick={() => setVerifyTarget({ id: report.id, decision: "VERIFIED" })}>
                          <CheckCircle2 size={14} /> Verify
                        </button>
                        <button className="btn btn-sm" onClick={() => setVerifyTarget({ id: report.id, decision: "REJECTED" })}>
                          <XCircle size={14} /> Reject
                        </button>
                      </div>
                    ) : null}
                  </div>
                ))}
                {!detail.reports.length ? (
                  <EmptyState icon={<FileWarning size={18} />} title="No field reports for this unit" body="Officer and citizen reports appear here after submission. They stay pending until a verification decision is recorded." />
                ) : null}
              </div>
            ) : null}

            {tab === "audit" ? (
              <div className="space-y-2">
                {!has("audit:read") ? <p className="text-xs text-muted">Your role cannot read the audit trail.</p> : null}
                {auditEntries.map((entry) => (
                  <div key={entry.id} className="rounded-lg border border-line px-3 py-2 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-medium">{entry.action}</span>
                      <span className="text-2xs text-muted">{fmtDateTime(entry.at)}</span>
                    </div>
                    <p className="mt-0.5 text-muted">{entry.reason} · {entry.actor}</p>
                  </div>
                ))}
                {has("audit:read") && !auditEntries.length ? <p className="text-xs text-muted">No unit-specific audit entries recorded yet.</p> : null}
              </div>
            ) : null}
          </div>

          <div className="border-t border-line px-4 py-3">
            <div className="eyebrow mb-1">Provenance</div>
            <dl className="grid grid-cols-1 gap-1 text-2xs text-muted">
              {Object.entries(detail.provenance).map(([key, value]) => (
                <div key={key} className="flex gap-2"><dt className="w-20 shrink-0 capitalize">{key}</dt><dd className="min-w-0 break-words">{value ?? "—"}</dd></div>
              ))}
            </dl>
            <p className="mt-2 text-2xs text-muted">{detail.disclaimer}</p>
          </div>
        </>
      ) : null}
    </Drawer>

    <ReasonDialog
      open={verifyTarget !== null}
      onClose={() => setVerifyTarget(null)}
      title={verifyTarget?.decision === "VERIFIED" ? "Verify field report" : "Reject field report"}
      description={
        verifyTarget?.decision === "VERIFIED"
          ? "Verification allows this report to contribute a bounded hazard adjustment (capped at +15 points, 7-day half-life) to the next assessment. The note is stored and audited."
          : "Rejection keeps the report in the record but excludes it from every hazard calculation. The reason is audited."
      }
      confirmLabel={verifyTarget?.decision === "VERIFIED" ? "Verify report" : "Reject report"}
      busy={verify.isPending}
      onConfirm={(note) => {
        if (!verifyTarget) return;
        verify.mutate({ id: verifyTarget.id, decision: verifyTarget.decision, note });
        setVerifyTarget(null);
      }}
    />
    </>
  );
}
