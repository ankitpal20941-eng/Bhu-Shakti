import { useMutation, useQuery } from "@tanstack/react-query";
import { BookOpenCheck, FlaskConical, ShieldAlert, TriangleAlert } from "lucide-react";
import { api } from "../lib/api";
import { fmtDateTime, fmtNumber } from "../lib/format";
import { useSession } from "../store/session";
import { Card, CardHeader, EmptyState, ErrorState, Loading, UncalibratedNote, toast } from "../components/ui";
import { useFallbackPolling } from "../hooks/useLiveUpdates";

interface FeatureSpec {
  key: string;
  label: string;
  unit: string;
  reference_mean: number;
  reference_scale: number;
  weight: number;
  provenance: string;
  note: string;
}

interface ModelsPayload {
  models: Array<{
    version: string;
    kind: string;
    name: string;
    features: string[];
    training_period: string;
    spatial_coverage: string;
    validation_approach: string;
    status: string;
    metrics: Record<string, unknown>;
    card: {
      intended_use?: string;
      not_intended_for?: string;
      training_dataset?: string;
      validation?: { status: string; blockers: string[]; method: string; n_positives: number; n_negatives: number };
      limitations?: string[];
      release_date?: string | null;
      owner?: string;
    };
    released_at: string | null;
    changelog: string;
  }>;
  evaluations: Array<{ model_version: string; method: string; status: string; metrics: Record<string, unknown>; notes: string; evaluated_at: string }>;
  active_version: string;
  parameters: {
    features: FeatureSpec[];
    intercept: number;
    trigger: { id_envelope: { a: number; b: number; regional_factor: number; source: string }; weights: Record<string, number>; combination: string; trigger_unavailable_multiplier: number; monsoon_months: number[] };
    field_evidence: { max_points: number; half_life_days: number; weights: Record<string, number> };
    exposure: { buffer_km: number; normaliser: number; weights: Record<string, number> };
    vulnerability: { weights: Record<string, number>; note: string };
    priority: { weights: Record<string, number>; thresholds: Record<string, number>; note: string };
  };
}

export default function Models() {
  const has = useSession((s) => s.has);
  const polling = useFallbackPolling(true);
  const query = useQuery({ queryKey: ["models"], queryFn: () => api<ModelsPayload>("/api/v1/admin/models"), ...polling });

  const activate = useMutation({
    mutationFn: (version: string) => api(`/api/v1/admin/models/${version}/activate`, { method: "POST" }),
    onSuccess: () => toast("Model is already active (no switch performed).", "info"),
    onError: (error) => toast(error instanceof Error ? error.message : "Activation refused", "error"),
  });
  const rollback = useMutation({
    mutationFn: (version: string) => api(`/api/v1/admin/models/${version}/rollback`, { method: "POST" }),
    onSuccess: () => toast("No previous production model exists in this build.", "info"),
    onError: (error) => toast(error instanceof Error ? error.message : "Rollback refused", "error"),
  });

  const data = query.data;
  const active = data?.models.find((model) => model.version === data.active_version);
  const validation = active?.card.validation;

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Model Registry</h1>
        <p className="text-sm text-muted">
          One executable prototype. No measured performance is published because no fitted model or verified inventory exists.
        </p>
      </div>

      {query.isLoading ? <Loading label="Loading registry" /> : null}
      {query.error ? <ErrorState error={query.error} onRetry={() => query.refetch()} /> : null}

      {data && active ? (
        <>
          <div className="rounded-xl border border-watch/40 bg-watch/5 p-4">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div className="flex items-start gap-2">
                <TriangleAlert size={18} className="mt-0.5 text-watch" />
                <div>
                  <div className="text-sm font-semibold text-watch">VALIDATION IN PROGRESS — no metric may be published</div>
                  <p className="mt-0.5 text-xs text-muted">
                    {validation?.blockers?.join(" ")}
                  </p>
                </div>
              </div>
              <span className="badge border-watch/40 text-watch bg-watch/10">{active.status}</span>
            </div>
            <div className="mt-2 grid gap-2 text-2xs text-muted sm:grid-cols-3">
              <div>Method implemented: {validation?.method}</div>
              <div>Verified positives: {fmtNumber(validation?.n_positives)}</div>
              <div>Sampled negatives: {fmtNumber(validation?.n_negatives)}</div>
            </div>
          </div>

          <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_360px]">
            <div className="space-y-3">
              <Card>
                <CardHeader
                  title={active.name}
                  subtitle={`${active.version} · ${active.kind} · released ${fmtDateTime(active.released_at)}`}
                  icon={<BookOpenCheck size={16} />}
                  action={has("models:write") ? (
                    <div className="flex gap-1">
                      <button className="btn btn-sm" onClick={() => activate.mutate(active.version)}>Activate</button>
                      <button className="btn btn-sm" onClick={() => rollback.mutate(active.version)}>Rollback</button>
                    </div>
                  ) : undefined}
                />
                <div className="grid gap-3 p-4 sm:grid-cols-2">
                  <div><div className="kpi-label">Training dataset</div><div className="text-sm">{active.card.training_dataset}</div></div>
                  <div><div className="kpi-label">Training period</div><div className="text-sm">{active.training_period}</div></div>
                  <div><div className="kpi-label">Spatial coverage</div><div className="text-sm">{active.spatial_coverage}</div></div>
                  <div><div className="kpi-label">Owner</div><div className="text-sm">{active.card.owner}</div></div>
                  <div className="sm:col-span-2"><div className="kpi-label">Intended use</div><div className="text-sm">{active.card.intended_use}</div></div>
                  <div className="sm:col-span-2"><div className="kpi-label">Not intended for</div><div className="text-sm">{active.card.not_intended_for}</div></div>
                </div>
                <div className="border-t border-line px-4 py-3">
                  <UncalibratedNote />
                </div>
              </Card>

              <Card>
                <CardHeader title="Feature specification" subtitle="Expert-set weights, standardised against the pilot reference distribution" />
                <div className="table-wrap">
                  <table className="data">
                    <thead><tr><th>Feature</th><th>Weight</th><th>Reference (mean ± scale)</th><th>Provenance</th><th>Rationale</th></tr></thead>
                    <tbody>
                      {data.parameters.features.map((feature) => (
                        <tr key={feature.key}>
                          <td className="font-medium">{feature.label}<div className="mono text-2xs text-muted">{feature.key}</div></td>
                          <td className="numeric">{feature.weight.toFixed(2)}</td>
                          <td className="numeric text-2xs text-muted">{feature.reference_mean} ± {feature.reference_scale} <span className="opacity-70">{feature.unit}</span></td>
                          <td className="text-2xs text-muted">{feature.provenance}</td>
                          <td className="max-w-[260px] text-2xs text-muted">{feature.note}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>

              <Card className="p-4">
                <div className="flex items-center gap-2 text-sm font-semibold"><FlaskConical size={16} /> Combination & thresholds</div>
                <dl className="mt-2 space-y-2 text-xs">
                  <div><dt className="kpi-label">Hazard combination</dt><dd className="mono">{data.parameters.trigger.combination}</dd></div>
                  <div><dt className="kpi-label">Intensity–duration envelope</dt><dd>I = {data.parameters.trigger.id_envelope.a} · D^{data.parameters.trigger.id_envelope.b} × {data.parameters.trigger.id_envelope.regional_factor} — {data.parameters.trigger.id_envelope.source}</dd></div>
                  <div><dt className="kpi-label">Trigger weights</dt><dd className="mono">{Object.entries(data.parameters.trigger.weights).map(([key, value]) => `${key} ${value}`).join(" · ")}</dd></div>
                  <div><dt className="kpi-label">Field evidence</dt><dd>Cap {data.parameters.field_evidence.max_points} points, half-life {data.parameters.field_evidence.half_life_days} days, verified reports only.</dd></div>
                  <div><dt className="kpi-label">Priority</dt><dd className="mono">{Object.entries(data.parameters.priority.weights).map(([key, value]) => `${key} ${value}`).join(" · ")} — thresholds {Object.entries(data.parameters.priority.thresholds).map(([key, value]) => `${key}≥${value}`).join(", ")}</dd></div>
                </dl>
                <p className="mt-2 text-2xs text-muted">{data.parameters.priority.note}</p>
              </Card>

              <Card className="p-4">
                <div className="text-sm font-semibold">Evaluation history</div>
                {(data.evaluations ?? []).map((evaluation) => (
                  <div key={`${evaluation.model_version}-${evaluation.evaluated_at}`} className="mt-2 rounded-lg border border-line px-3 py-2 text-xs">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span>{evaluation.method}</span>
                      <span className="badge border-watch/40 text-watch bg-watch/10">{evaluation.status}</span>
                    </div>
                    <div className="mt-1 text-2xs text-muted">{evaluation.notes || "No blockers recorded."}</div>
                    <div className="mt-1 text-2xs text-muted">Metrics: {Object.keys(evaluation.metrics).length ? JSON.stringify(evaluation.metrics) : "none published"}</div>
                    <div className="text-2xs text-muted">{fmtDateTime(evaluation.evaluated_at)}</div>
                  </div>
                ))}
                {!data.evaluations.length ? <EmptyState title="No evaluations" /> : null}
              </Card>
            </div>

            <div className="space-y-3">
              <Card className="p-4">
                <div className="flex items-center gap-2 text-sm font-semibold"><ShieldAlert size={16} /> Limitations</div>
                <ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-muted">
                  {(active.card.limitations ?? []).map((item) => <li key={item}>{item}</li>)}
                </ul>
              </Card>
              <Card className="p-4">
                <div className="text-sm font-semibold">Release policy</div>
                <p className="mt-1 text-xs text-muted">
                  Releasing a model requires a fitted pipeline, spatial-block and temporal-holdout validation, a
                  reviewed model card and a recorded approval. The registry refuses activation of a version with no
                  executable inference implementation rather than pretending a switch occurred.
                </p>
                <p className="mt-2 text-2xs text-muted">{active.changelog}</p>
              </Card>
              <Card className="p-4">
                <div className="text-sm font-semibold">Registered versions</div>
                <div className="mt-2 space-y-1 text-xs">
                  {data.models.map((model) => (
                    <div key={model.version} className="flex items-center justify-between gap-2">
                      <span className="mono truncate">{model.version}</span>
                      <span className="chip">{model.status}</span>
                    </div>
                  ))}
                </div>
              </Card>
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}
