import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { BarChart3, Compass, Droplets, RefreshCw } from "lucide-react";
import { api } from "../lib/api";
import {
  AppleGlassStat,
  DisclosurePill,
  ReliabilityBadge,
  SegmentedControl,
  ShimmerButton,
  SpotlightCard,
} from "../components/aceternity";
import {
  Progress,
  Alert,
  AlertTitle,
  AlertDescription,
} from "../components/shadcn";

interface RainfallIntelligenceData {
  evaluation: {
    district_code: string;
    district_name: string;
    geology_type: string;
    trigger_index: number;
    threshold_status: string;
    calibrated_thresholds: {
      watch_24h_mm: number;
      warning_24h_mm: number;
      critical_24h_mm: number;
      antecedent_72h_mm: number;
    };
    observed_accumulations: {
      rainfall_1h_mm: number;
      rainfall_6h_mm: number;
      rainfall_24h_mm: number;
      rainfall_72h_mm: number;
      soil_moisture_pct: number;
    };
    anomaly: {
      climatological_daily_mean_mm: number;
      departure_from_normal_pct: number;
      anomaly_category: string;
    };
    calibration_provenance: string;
  };
  forecast_horizons: Array<{
    horizon_h: number;
    target_time: string;
    rainfall_mm: number;
    source: string;
  }>;
  hourly_intensity_trend: Array<{
    hours_ago: number;
    hourly_intensity_mm_h: number;
    cumulative_24h_mm: number;
  }>;
  data_notice: string;
}

export default function RainfallIntelligence() {
  const [district, setDistrict] = useState<string>("AS-KMR");

  const { data, isLoading, refetch } = useQuery<RainfallIntelligenceData>({
    queryKey: ["rainfall-intel", district],
    queryFn: () => api(`/api/v1/rainfall/intelligence?district_code=${district}`),
  });

  const ev = data?.evaluation;
  const obs = ev?.observed_accumulations;
  const th = ev?.calibrated_thresholds;

  return (
    <div className="space-y-6">
      {/* Header and Disclosures */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 pb-2 border-b border-line">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="flex items-center gap-1.5 text-[11px] font-semibold text-safe bg-safe/10 border border-safe/25 px-2.5 py-0.5 rounded-full">
              <Droplets size={12} />
              Geotechnical Rainfall Intelligence
            </span>
            <DisclosurePill
              text="GSI & IMD Empirical Intensity-Duration (I-D) Threshold Model"
              tooltip="Thresholds are strictly calibrated to regional soil shear strengths and lithological conditions. Universal static rainfall thresholds are scientifically prohibited."
            />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-ink">
            Rainfall Intelligence Dashboard
          </h1>
          <p className="text-xs text-muted mt-0.5">
            Multi-accumulation precipitation telemetry, antecedent soil saturation, climatological departure anomaly detection, and locally calibrated geotechnical thresholds.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <ReliabilityBadge
            score={`${ev?.trigger_index ?? 0}/100`}
            label="Saturation Hazard Score"
            verified={true}
          />
          <ShimmerButton
            variant="secondary"
            onClick={() => refetch()}
            className="text-xs"
          >
            <RefreshCw size={13} className={isLoading ? "animate-spin" : ""} />
            Sync Radar
          </ShimmerButton>
        </div>
      </div>

      {/* District Segmented Controller */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <SegmentedControl
          options={[
            { value: "AS-KMR", label: "Kamrup Metro (Assam)" },
            { value: "ML-EKH", label: "East Khasi Hills (Meghalaya)" },
            { value: "MZ-AIZ", label: "Aizawl (Mizoram)" },
          ]}
          value={district}
          onChange={setDistrict}
        />
        <div className="text-[11px] text-muted">
          Lithology: <strong className="text-ink">{ev?.geology_type ?? "Metasedimentary & Sandstone"}</strong>
        </div>
      </div>

      {/* Multi-Horizon Accumulation Apple Glass Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3.5">
        <AppleGlassStat
          label="1-Hour Rain"
          value={isLoading ? "—" : `${obs?.rainfall_1h_mm ?? 0} mm`}
          delta="Recent intensity rate"
          deltaType="neutral"
        />
        <AppleGlassStat
          label="6-Hour Rain"
          value={isLoading ? "—" : `${obs?.rainfall_6h_mm ?? 0} mm`}
          delta="Short-term runoff"
          deltaType="neutral"
        />
        <AppleGlassStat
          label="24-Hour Rain"
          value={isLoading ? "—" : `${obs?.rainfall_24h_mm ?? 0} mm`}
          delta={`Warn limit: ${th?.warning_24h_mm ?? 0} mm`}
          deltaType={
            (obs?.rainfall_24h_mm ?? 0) >= (th?.warning_24h_mm ?? 0)
              ? "negative"
              : "positive"
          }
        />
        <AppleGlassStat
          label="72-Hour Rain"
          value={isLoading ? "—" : `${obs?.rainfall_72h_mm ?? 0} mm`}
          delta={`Trigger: ${th?.antecedent_72h_mm ?? 0} mm`}
          deltaType={
            (obs?.rainfall_72h_mm ?? 0) >= (th?.antecedent_72h_mm ?? 0)
              ? "negative"
              : "positive"
          }
        />
        <AppleGlassStat
          label="Soil Moisture"
          value={isLoading ? "—" : `${obs?.soil_moisture_pct ?? 0}%`}
          delta="Subsurface volumetric"
          deltaType="neutral"
        />
      </div>

      {/* Threshold Status Banner */}
      <div className="p-4 bg-surface-2/80 dark:bg-surface-2/50 backdrop-blur-md border border-line rounded-2xl flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="text-[10px] text-forest uppercase tracking-wider font-bold">
            Locally Calibrated Trigger Status
          </div>
          <h2 className="text-base font-bold text-ink mt-0.5">
            {ev?.district_name}: <span className="text-warning">{ev?.threshold_status.replace("_", " ")}</span>
          </h2>
          <div className="text-xs text-muted mt-1 font-mono">
            Calibration: {ev?.calibration_provenance}
          </div>
        </div>

        <div className="flex items-center gap-4 text-xs">
          <div className="p-3 bg-surface-3/70 dark:bg-surface-3/40 rounded-xl border border-line text-center">
            <div className="text-[10px] text-muted uppercase font-semibold">24h Climatological Departure</div>
            <div className="text-sm font-bold font-mono text-critical mt-0.5">
              {ev?.anomaly.departure_from_normal_pct ? `+${ev?.anomaly.departure_from_normal_pct}%` : "—"}
            </div>
            <div className="text-[9px] text-muted uppercase font-mono">{ev?.anomaly.anomaly_category}</div>
          </div>
          <div className="p-3 bg-surface-3/70 dark:bg-surface-3/40 rounded-xl border border-line text-center">
            <div className="text-[10px] text-muted uppercase font-semibold">Precipitation Trigger Index</div>
            <div className="text-sm font-bold font-mono text-forest mt-0.5">
              {ev?.trigger_index ?? 0} / 100
            </div>
            <div className="text-[9px] text-muted uppercase font-mono">Composite Envelope</div>
          </div>
        </div>
      </div>

      {/* Intensity Trends & Forecast Visualizer */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Hourly Intensity Trend Chart (24h back) */}
        <SpotlightCard>
          <div className="flex items-center justify-between pb-3 mb-3 border-b border-line">
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-xl bg-forest-soft text-forest">
                <BarChart3 size={16} />
              </div>
              <div>
                <h3 className="font-bold text-xs uppercase tracking-wider text-ink">
                  24-Hour Rainfall Intensity & Cumulative Curves
                </h3>
                <p className="text-[11px] text-muted">
                  Recorded gauge telemetry (mm/h and cumulative total)
                </p>
              </div>
            </div>
          </div>

          <div className="space-y-2 max-h-[320px] overflow-y-auto pr-1">
            {(data?.hourly_intensity_trend ?? []).slice(0, 12).map((item) => (
              <div key={item.hours_ago} className="p-2.5 bg-surface-2/60 dark:bg-surface-2/30 rounded-xl border border-line/60 space-y-1.5">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted font-mono">{item.hours_ago}h ago</span>
                  <span className="font-semibold text-ink font-mono tabular-nums">
                    {item.hourly_intensity_mm_h} mm/h (Σ {item.cumulative_24h_mm} mm)
                  </span>
                </div>
                <Progress value={item.hourly_intensity_mm_h} max={25} indicatorColor="bg-forest" className="h-2" />
              </div>
            ))}
          </div>
        </SpotlightCard>

        {/* Future Precipitation Forecast Horizons */}
        <SpotlightCard>
          <div className="flex items-center justify-between pb-3 mb-3 border-b border-line">
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-xl bg-safe/10 text-safe">
                <Compass size={16} />
              </div>
              <div>
                <h3 className="font-bold text-xs uppercase tracking-wider text-ink">
                  Precipitation Forecast Horizons (Next 48h)
                </h3>
                <p className="text-[11px] text-muted">
                  NWP projections clearly differentiated from actual observed gauge readings
                </p>
              </div>
            </div>
          </div>

          <div className="space-y-3">
            {(data?.forecast_horizons ?? []).map((fc) => (
              <div
                key={fc.horizon_h}
                className="p-3 bg-surface-2/70 dark:bg-surface-2/40 border border-line rounded-xl flex items-center justify-between text-xs"
              >
                <div>
                  <div className="font-semibold text-ink">
                    +{fc.horizon_h} Hours Projection
                  </div>
                  <div className="text-[10px] text-muted uppercase font-mono mt-0.5">
                    Model: {fc.source}
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-sm font-bold font-mono text-ink">
                    {fc.rainfall_mm} mm
                  </span>
                  <div className="text-[10px] text-muted">Estimated Accumulation</div>
                </div>
              </div>
            ))}

            <Alert variant="default" className="border-line bg-surface-2/80 dark:bg-surface-2/50 backdrop-blur-md">
              <div className="space-y-1">
                <AlertTitle className="text-xs font-semibold text-ink">
                  Mandatory Geotechnical Calibration Protocol
                </AlertTitle>
                <AlertDescription className="text-xs text-muted leading-relaxed">
                  Platform policy strictly enforces local geotechnical calibration.
                  Universal static rainfall thresholds across distinct mountain ranges are scientifically invalid and strictly forbidden.
                </AlertDescription>
              </div>
            </Alert>
          </div>
        </SpotlightCard>
      </div>
    </div>
  );
}
