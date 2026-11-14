import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FlaskConical, Play, TriangleAlert } from "lucide-react";
import { api } from "../lib/api";
import { fmtDateTime, fmtNumber, timeAgo } from "../lib/format";
import type { PriorityLevel } from "../lib/types";
import { useSession } from "../store/session";
import { Card, CardHeader, EmptyState, ErrorState, Loading, PriorityBadge, toast } from "../components/ui";

interface ScenarioResult {
  id: number;
  name: string;
  created_at: string;
  badge: string;
  inputs: { rainfall_24h: number; soil_moisture_pct: number; use_field_evidence: boolean; district_codes: string[] | null; assumptions: string[] };
  baseline: { zones: number; avg_hazard: number; warnings: number; avg_priority: number };
  scenario: {
    mode: string;
    zones: number;
    avg_hazard: number;
    avg_hazard_delta: number;
    warnings: number;
    new_warnings: number;
    top_changes: Array<{
      zone_id: number; zone_name: string;
      baseline_hazard: number | null; scenario_hazard: number;
      hazard_delta: number;
      baseline_priority: PriorityLevel | null; scenario_priority: PriorityLevel;
      recommended_action: string | null;
    }>;
    safety_note: string;
  };
}

export default function Scenarios() {
  const user = useSession((s) => s.user);
  const queryClient = useQueryClient();
  const [name, setName] = useState("Monsoon stress test");
  const [district, setDistrict] = useState(user?.districts?.[0] ?? "AS-KMR");
  const [rainfall, setRainfall] = useState(220);
  const [soil, setSoil] = useState(48);
  const [fieldEvidence, setFieldEvidence] = useState(false);
  const [result, setResult] = useState<ScenarioResult | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const districts = useQuery({
    queryKey: ["public-config"],
    queryFn: () => api<{ districts: Array<{ code: string; name: string }> }>("/api/v1/public/config"),
    staleTime: 300_000,
  });
  const history = useQuery({
    queryKey: ["scenarios"],
    queryFn: () => api<{ scenarios: Array<{ id: number; name: string; created_at: string; summary: { avg_hazard: number; avg_hazard_delta: number; new_warnings: number } }> }>("/api/v1/scenarios"),
  });
  const detail = useQuery({
    queryKey: ["scenario", selectedId],
    queryFn: () => api<ScenarioResult>(`/api/v1/scenarios/${selectedId}`),
    enabled: selectedId !== null,
  });

  const run = useMutation({
    mutationFn: () => api<ScenarioResult>("/api/v1/scenarios", {
      method: "POST",
      json: {
        name,
        district_codes: district ? [district] : undefined,
        rainfall_24h: rainfall,
        soil_moisture_pct: soil,
        use_field_evidence: fieldEvidence,
      },
    }),
    onSuccess: (data) => {
      setResult(data);
      queryClient.invalidateQueries({ queryKey: ["scenarios"] });
      toast("Scenario completed. Output is isolated from operational risk.", "ok");
    },
    onError: (error) => toast(error instanceof Error ? error.message : "Scenario failed", "error"),
  });

  const view = result ?? detail.data ?? null;

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Scenario Lab</h1>
        <p className="text-sm text-muted">
          What-if analysis for planning and training. Scenarios never change live risk, road status or alerts.
        </p>
      </div>

      <div className="flex items-center gap-2 rounded-lg border border-critical/40 bg-critical/5 px-3 py-2 text-xs font-semibold text-critical">
        <TriangleAlert size={15} /> SIMULATION — NOT LIVE
        <span className="font-normal text-muted">Outputs are stored separately and never create operational alerts.</span>
      </div>

      <div className="grid gap-3 lg:grid-cols-[360px_minmax(0,1fr)]">
        <Card>
          <CardHeader title="Scenario inputs" icon={<FlaskConical size={16} />} />
          <div className="space-y-3 p-4">
            <div>
              <label className="label" htmlFor="scenario-name">Name</label>
              <input id="scenario-name" className="input" value={name} onChange={(event) => setName(event.target.value)} />
            </div>
            <div>
              <label className="label" htmlFor="scenario-district">District</label>
              <select id="scenario-district" className="select" value={district} onChange={(event) => setDistrict(event.target.value)}>
                {(districts.data?.districts ?? []).filter((item) => user?.statewide || user?.districts.includes(item.code)).map((item) => (
                  <option key={item.code} value={item.code}>{item.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="label" htmlFor="rainfall">24-hour rainfall: <b className="numeric">{rainfall} mm</b></label>
              <input id="rainfall" type="range" min={0} max={400} step={10} value={rainfall} onChange={(event) => setRainfall(Number(event.target.value))} className="w-full accent-[var(--forest)]" />
              <p className="hint">Uniformly distributed across sub-daily windows; 72 h antecedent assumed 2× the 24 h total.</p>
            </div>
            <div>
              <label className="label" htmlFor="soil">Soil moisture: <b className="numeric">{soil}%</b></label>
              <input id="soil" type="range" min={10} max={80} step={1} value={soil} onChange={(event) => setSoil(Number(event.target.value))} className="w-full accent-[var(--forest)]" />
            </div>
            <label className="flex items-start gap-2 text-xs">
              <input type="checkbox" className="mt-0.5" checked={fieldEvidence} onChange={(event) => setFieldEvidence(event.target.checked)} />
              Include verified field evidence in the scenario
            </label>
            <button className="btn btn-primary w-full" onClick={() => run.mutate()} disabled={run.isPending || name.trim().length < 3}>
              <Play size={15} /> {run.isPending ? "Running scenario…" : "Run scenario"}
            </button>
            <p className="hint">
              This requires the <span className="mono">scenarios:run</span> permission. Scenario assessments are stored
              with an isolation flag and excluded from every operational query.
            </p>
          </div>
        </Card>

        <div className="space-y-3">
          {view ? (
            <>
              <Card>
                <CardHeader title={view.name} subtitle={`${view.badge} · ${fmtDateTime(view.created_at)}`} />
                <div className="grid grid-cols-2 gap-2 p-4 sm:grid-cols-4">
                  <div className="rounded-lg border border-line bg-canvas px-3 py-2">
                    <div className="kpi-label">Baseline avg hazard</div>
                    <div className="stat-value">{fmtNumber(view.baseline.avg_hazard, 1)}</div>
                  </div>
                  <div className="rounded-lg border border-line bg-canvas px-3 py-2">
                    <div className="kpi-label">Scenario avg hazard</div>
                    <div className="stat-value">{fmtNumber(view.scenario.avg_hazard, 1)}</div>
                  </div>
                  <div className="rounded-lg border border-line bg-canvas px-3 py-2">
                    <div className="kpi-label">Delta</div>
                    <div className={`stat-value ${view.scenario.avg_hazard_delta >= 0 ? "text-warning" : "text-safe"}`}>
                      {view.scenario.avg_hazard_delta >= 0 ? "+" : ""}{fmtNumber(view.scenario.avg_hazard_delta, 1)}
                    </div>
                  </div>
                  <div className="rounded-lg border border-line bg-canvas px-3 py-2">
                    <div className="kpi-label">New warning units</div>
                    <div className="stat-value">{fmtNumber(view.scenario.new_warnings)}</div>
                  </div>
                </div>
                <div className="border-t border-line px-4 py-2 text-2xs text-muted">
                  Baseline {view.baseline.warnings} warning units → scenario {view.scenario.warnings}. {view.scenario.safety_note}
                </div>
              </Card>

              <Card>
                <CardHeader title="Largest hazard changes" subtitle="Baseline vs scenario, same susceptibility baseline" />
                <div className="table-wrap">
                  <table className="data">
                    <thead><tr><th>Unit</th><th>Baseline</th><th>Scenario</th><th>Delta</th><th>Priority</th><th>Recommended response</th></tr></thead>
                    <tbody>
                      {view.scenario.top_changes.map((change) => (
                        <tr key={change.zone_id}>
                          <td className="font-medium">{change.zone_name}</td>
                          <td className="numeric">{fmtNumber(change.baseline_hazard, 0)}</td>
                          <td className="numeric">{fmtNumber(change.scenario_hazard, 0)}</td>
                          <td className="numeric">+{fmtNumber(change.hazard_delta, 1)}</td>
                          <td><PriorityBadge level={change.scenario_priority} /></td>
                          <td className="max-w-[300px] text-2xs text-muted">{change.recommended_action}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {!view.scenario.top_changes.length ? <EmptyState title="No units in this scenario" /> : null}
              </Card>

              <Card className="p-4">
                <div className="text-sm font-semibold">Scenario assumptions</div>
                <ul className="mt-1 list-disc space-y-1 pl-4 text-xs text-muted">
                  {view.inputs.assumptions.map((item) => <li key={item}>{item}</li>)}
                </ul>
                <p className="mt-2 text-2xs text-muted">
                  Scenario rainfall is hypothetical and is not an observation. It cannot be approved as an alert from here.
                </p>
              </Card>
            </>
          ) : (
            <Card><EmptyState icon={<FlaskConical size={18} />} title="No scenario selected" body="Run a scenario to compare baseline and hypothetical hazard, priority and response needs." /></Card>
          )}

          <Card>
            <CardHeader title="Recent scenarios" />
            {history.isLoading ? <Loading /> : null}
            {history.error ? <ErrorState error={history.error} onRetry={() => history.refetch()} /> : null}
            <div className="divide-y divide-line">
              {(history.data?.scenarios ?? []).map((scenario) => (
                <button key={scenario.id} className="flex w-full items-center justify-between gap-2 px-4 py-2 text-left hover:bg-surface-2" onClick={() => { setResult(null); setSelectedId(scenario.id); }}>
                  <div>
                    <div className="text-sm font-medium">{scenario.name}</div>
                    <div className="text-2xs text-muted">{timeAgo(scenario.created_at)} · Δ {fmtNumber(scenario.summary.avg_hazard_delta, 1)} · {scenario.summary.new_warnings} new warnings</div>
                  </div>
                  <span className="chip">SIMULATION</span>
                </button>
              ))}
              {!(history.data?.scenarios ?? []).length ? <EmptyState title="No scenarios yet" /> : null}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
