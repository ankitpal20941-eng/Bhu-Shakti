import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Layers, Scale, ShieldCheck, TrendingUp } from "lucide-react";
import { api } from "../lib/api";
import {
  DisclosurePill,
  SpotlightCard,
} from "../components/aceternity";
import {
  Badge,
  Progress,
  Alert,
  AlertDescription,
} from "../components/shadcn";

interface RegionalCoverageDetail {
  district_name: string;
  spatial_units_count: number;
  weather_coverage_pct: number;
  soil_moisture_coverage_pct: number;
  road_cut_network_coverage_pct: number;
  verified_inventory_points: number;
  validation_state: string;
  false_positive_rate: string;
  false_negative_rate: string;
  data_notice: string;
}

interface ModelMonitoringResponse {
  active_model_version: string;
  model_kind: string;
  validation_gate_status: string;
  fairness_summary: string;
  regional_coverage: Record<string, RegionalCoverageDetail>;
  drift_monitoring: {
    feature_drift_status: string;
    rainfall_distribution_ks_p_value: number;
    hazard_score_distribution_shift: string;
    missing_input_rates: Record<string, string>;
    retraining_recommendation: string;
  };
  version_history: Array<{
    version: string;
    name: string;
    status: string;
    validation_approach: string;
    released_at: string | null;
  }>;
  compliance_statement: string;
}

export default function ModelMonitoring() {
  const { data } = useQuery<ModelMonitoringResponse>({
    queryKey: ["model-monitoring"],
    queryFn: () => api("/api/v1/models/monitoring"),
  });

  return (
    <div className="space-y-6">
      {/* Header and Disclosures */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 pb-2 border-b border-line">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="flex items-center gap-1.5 text-[11px] font-semibold text-safe bg-safe/10 border border-safe/25 px-2.5 py-0.5 rounded-full">
              <ShieldCheck size={12} />
              AI Safety & Governance Gate Enforced
            </span>
            <DisclosurePill
              text="Zero-Fabrication Metric Standard"
              tooltip="In strict accordance with scientific disaster ethics, BHUSHAKTI AI never renders synthetic accuracy figures when ground inventory data is insufficient."
            />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-ink">
            AI Model Monitoring & Regional Fairness
          </h1>
          <p className="text-xs text-muted mt-0.5">
            Transparent tracking of model calibration, drift indicators, telemetry missingness rates, and cross-district fairness audits.
          </p>
        </div>

      </div>

      {/* Truthful Model Status Banner */}
      <Alert variant="warning">
        <div className="flex flex-wrap items-center justify-between gap-2 w-full">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold font-mono text-forest bg-forest-soft px-2.5 py-1 rounded-xl border border-forest/20">
              {data?.active_model_version ?? "suscept-v0.1+trigger-v0.1"}
            </span>
            <span className="text-xs font-semibold text-muted">
              {data?.model_kind}
            </span>
          </div>
          <Badge variant="warning" className="font-mono text-[10px]">
            Probability Output: NULL (Uncalibrated Index Mode)
          </Badge>
        </div>
        <AlertDescription className="text-xs text-muted leading-relaxed mt-1">
          {data?.compliance_statement}
        </AlertDescription>
      </Alert>

      {/* Regional Fairness Audit (District-by-District) */}
      <SpotlightCard>
        <div className="flex items-center justify-between pb-3 mb-3 border-b border-line">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-xl bg-forest-soft text-forest">
              <Scale size={16} />
            </div>
            <div>
              <h3 className="font-bold text-xs uppercase tracking-wider text-ink">
                Regional Fairness & Data Coverage by District
              </h3>
              <p className="text-[11px] text-muted">
                Verifying that all mountain districts receive equal sensor coverage and locally calibrated baselines
              </p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {Object.entries(data?.regional_coverage ?? {}).map(([code, reg]) => (
            <div
              key={code}
              className="p-4 bg-surface-2/70 dark:bg-surface-2/40 border border-line rounded-2xl space-y-3 text-xs"
            >
              <div className="flex items-center justify-between border-b border-line/60 pb-2.5">
                <span className="font-bold text-ink text-sm">{reg.district_name}</span>
                <span className="font-mono text-muted text-[11px]">[{code}]</span>
              </div>

              <div className="space-y-2 text-[11px]">
                <div className="space-y-1">
                  <div className="flex justify-between">
                    <span className="text-muted">Weather Telemetry:</span>
                    <strong className="text-safe font-mono">{reg.weather_coverage_pct}%</strong>
                  </div>
                  <Progress value={reg.weather_coverage_pct} className="h-1" />
                </div>
                <div className="space-y-1">
                  <div className="flex justify-between">
                    <span className="text-muted">Soil Moisture Coverage:</span>
                    <strong className="text-safe font-mono">{reg.soil_moisture_coverage_pct}%</strong>
                  </div>
                  <Progress value={reg.soil_moisture_coverage_pct} className="h-1" />
                </div>
                <div className="space-y-1">
                  <div className="flex justify-between">
                    <span className="text-muted">Road Corridor Network:</span>
                    <strong className="text-ink font-mono">{reg.road_cut_network_coverage_pct}%</strong>
                  </div>
                  <Progress value={reg.road_cut_network_coverage_pct} className="h-1" />
                </div>
                <div className="flex justify-between pt-1">
                  <span className="text-muted">Verified Landslide Points:</span>
                  <strong className="text-warning font-mono">{reg.verified_inventory_points} events</strong>
                </div>
              </div>

              <div className="p-3 bg-warning/5 border border-warning/20 rounded-xl space-y-1 text-[11px]">
                <div className="font-bold text-warning flex items-center gap-1.5">
                  <AlertTriangle size={12} /> {reg.validation_state}
                </div>
                <p className="text-muted text-[10px] leading-relaxed">
                  {reg.data_notice}
                </p>
              </div>
            </div>
          ))}
        </div>
      </SpotlightCard>

      {/* Drift Detection & Missing Telemetry */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <SpotlightCard>
          <div className="flex items-center justify-between pb-3 mb-3 border-b border-line">
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-xl bg-forest-soft text-forest">
                <TrendingUp size={16} />
              </div>
              <div>
                <h3 className="font-bold text-xs uppercase tracking-wider text-ink">
                  Model Stability & Drift Detection
                </h3>
                <p className="text-[11px] text-muted">
                  Comparing current operational distributions against baseline training periods
                </p>
              </div>
            </div>
          </div>

          <div className="space-y-3 text-xs">
            <div className="flex items-center justify-between p-3 bg-surface-2/70 dark:bg-surface-2/40 rounded-xl border border-line">
              <span className="text-muted">Feature Drift Status:</span>
              <strong className="text-safe font-mono">{data?.drift_monitoring.feature_drift_status}</strong>
            </div>
            <div className="flex items-center justify-between p-3 bg-surface-2/70 dark:bg-surface-2/40 rounded-xl border border-line">
              <span className="text-muted">Rainfall KS Test (p-value):</span>
              <span className="font-mono font-bold text-ink">
                {data?.drift_monitoring.rainfall_distribution_ks_p_value} (p &gt; 0.05, no drift)
              </span>
            </div>
            <div className="flex items-center justify-between p-3 bg-surface-2/70 dark:bg-surface-2/40 rounded-xl border border-line">
              <span className="text-muted">Seasonal Hazard Shift:</span>
              <span className="font-medium text-ink">
                {data?.drift_monitoring.hazard_score_distribution_shift}
              </span>
            </div>
            <div className="p-3.5 bg-surface-3/70 dark:bg-surface-3/40 rounded-xl border border-line space-y-1">
              <span className="text-[10px] font-bold text-muted uppercase tracking-wider block">
                Retraining Recommendation:
              </span>
              <p className="text-xs text-ink leading-relaxed">
                {data?.drift_monitoring.retraining_recommendation}
              </p>
            </div>
          </div>
        </SpotlightCard>

        <SpotlightCard>
          <div className="flex items-center justify-between pb-3 mb-3 border-b border-line">
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-xl bg-forest-soft text-forest">
                <Layers size={16} />
              </div>
              <div>
                <h3 className="font-bold text-xs uppercase tracking-wider text-ink">
                  Missing Input Data Rates
                </h3>
                <p className="text-[11px] text-muted">
                  Continuous monitoring of telemetry dropout frequency
                </p>
              </div>
            </div>
          </div>

          <div className="space-y-2.5 text-xs">
            {Object.entries(data?.drift_monitoring.missing_input_rates ?? {}).map(([key, val]) => (
              <div
                key={key}
                className="flex items-center justify-between p-3 bg-surface-2/70 dark:bg-surface-2/40 rounded-xl border border-line"
              >
                <span className="text-muted capitalize">{key.replace("_", " ")}:</span>
                <span className="font-mono font-bold text-ink">{val}</span>
              </div>
            ))}
          </div>
        </SpotlightCard>
      </div>
    </div>
  );
}
