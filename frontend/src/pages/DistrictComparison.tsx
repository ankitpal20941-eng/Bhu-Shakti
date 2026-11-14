import { CloudRain, Compass, Layers } from "lucide-react";
import { DisclosurePill, SpotlightCard } from "../components/aceternity";

const DISTRICT_PROFILES = [
  {
    code: "AS-KMR",
    name: "Kamrup Metropolitan",
    state: "Assam",
    hq: "Guwahati",
    terrain_desc: "Precambrian granitic gneiss hills, deeply weathered red soil overburden, steep urban road-cut slopes.",
    elevation_range: "50m – 380m ASL",
    mean_slope: "28.5°",
    population_exposed: 245000,
    rainfall_regime: "Subtropical monsoon (moderate-high)",
    threshold_24h_warn: 95.0,
    threshold_24h_crit: 140.0,
    antecedent_72h: 160.0,
    units_count: 48,
    teams_ready: 2,
    hospitals_count: 4,
  },
  {
    code: "ML-EKH",
    name: "East Khasi Hills",
    state: "Meghalaya",
    hq: "Shillong",
    terrain_desc: "Shillong Group quartzites & sandstones, deep plateau gorge canyons, extreme orographic rainfall regime.",
    elevation_range: "950m – 1960m ASL",
    mean_slope: "36.2°",
    population_exposed: 128000,
    rainfall_regime: "Extreme Cherrapunji-Mawsynram pluvial belt",
    threshold_24h_warn: 145.0,
    threshold_24h_crit: 210.0,
    antecedent_72h: 280.0,
    units_count: 36,
    teams_ready: 1,
    hospitals_count: 2,
  },
  {
    code: "MZ-AIZ",
    name: "Aizawl",
    state: "Mizoram",
    hq: "Aizawl",
    terrain_desc: "Tertiary Surma Group interbedded shale-siltstone-sandstone with parallel ridge-and-valley dip-slopes.",
    elevation_range: "400m – 1280m ASL",
    mean_slope: "34.8°",
    population_exposed: 184000,
    rainfall_regime: "Tropical wet monsoon & post-cyclone storms",
    threshold_24h_warn: 110.0,
    threshold_24h_crit: 165.0,
    antecedent_72h: 195.0,
    units_count: 32,
    teams_ready: 1,
    hospitals_count: 2,
  },
];

export default function DistrictComparison() {
  return (
    <div className="space-y-6">
      {/* Header and Disclosures */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 pb-2 border-b border-line">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="flex items-center gap-1.5 text-[11px] font-semibold text-forest bg-forest-soft border border-forest/25 px-2.5 py-0.5 rounded-full">
              <Compass size={12} />
              Comparative Regional Geomorphology
            </span>
            <DisclosurePill
              text="Indicative demo profiles — not verified GSI baselines"
              tooltip="Side-by-side comparison of mountain geotechnical domains, highlighting why universal thresholds are invalid and showcasing local terrain-calibrated safety criteria."
            />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-ink">
            Cross-District Geotechnical Comparison
          </h1>
          <p className="text-xs text-muted mt-0.5">
            Comparative analysis of the three pilot districts across Assam, Meghalaya, and Mizoram: terrain regimes, locally calibrated thresholds, and operational resources.
          </p>
        </div>

      </div>

      {/* Comparison Spotlight Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {DISTRICT_PROFILES.map((p) => (
          <SpotlightCard key={p.code} className="flex flex-col justify-between p-5 space-y-4">
            <div>
              <div className="pb-3 border-b border-line flex items-center justify-between">
                <div>
                  <span className="text-xs font-mono font-bold text-forest">{p.code}</span>
                  <h3 className="text-base font-bold text-ink mt-0.5">{p.name}</h3>
                  <div className="text-xs text-muted">HQ: {p.hq} • {p.state}</div>
                </div>
              </div>

              <div className="mt-4 space-y-4 text-xs">
                {/* Terrain & Geology */}
                <div>
                  <span className="font-bold text-ink flex items-center gap-1.5 mb-1 text-[11px] uppercase tracking-wider text-muted">
                    <Layers size={13} className="text-forest" /> Geological Setting
                  </span>
                  <p className="text-muted leading-relaxed">{p.terrain_desc}</p>
                  <div className="mt-2.5 flex gap-4 text-[11px] text-muted">
                    <span>Elevation: <strong className="text-ink font-mono">{p.elevation_range}</strong></span>
                    <span>Mean Slope: <strong className="text-ink font-mono">{p.mean_slope}</strong></span>
                  </div>
                </div>

                {/* Calibrated Rainfall Envelopes */}
                <div className="p-3.5 bg-surface-2/70 dark:bg-surface-2/40 border border-line rounded-2xl space-y-2">
                  <span className="font-bold flex items-center gap-1.5 text-[11px] uppercase tracking-wider text-warning">
                    <CloudRain size={13} className="text-warning" /> Calibrated Rainfall Envelopes
                  </span>
                  <div className="grid grid-cols-3 gap-2 text-center pt-1">
                    <div className="bg-surface-3/70 dark:bg-surface-3/40 p-2 rounded-xl border border-line/50">
                      <div className="text-[9px] text-muted uppercase font-semibold">Warning 24h</div>
                      <div className="font-bold text-warning text-xs font-mono mt-0.5">{p.threshold_24h_warn} mm</div>
                    </div>
                    <div className="bg-surface-3/70 dark:bg-surface-3/40 p-2 rounded-xl border border-line/50">
                      <div className="text-[9px] text-muted uppercase font-semibold">Critical 24h</div>
                      <div className="font-bold text-critical text-xs font-mono mt-0.5">{p.threshold_24h_crit} mm</div>
                    </div>
                    <div className="bg-surface-3/70 dark:bg-surface-3/40 p-2 rounded-xl border border-line/50">
                      <div className="text-[9px] text-muted uppercase font-semibold">Antecedent 72h</div>
                      <div className="font-bold text-ink text-xs font-mono mt-0.5">{p.antecedent_72h} mm</div>
                    </div>
                  </div>
                  <div className="text-[10px] text-muted/80 italic">{p.rainfall_regime}</div>
                </div>

                {/* Operational Readiness */}
                <div className="grid grid-cols-3 gap-2 text-center">
                  <div className="p-2.5 border border-line rounded-xl bg-surface-2/60">
                    <div className="text-[10px] text-muted uppercase font-semibold">Slope Units</div>
                    <div className="text-sm font-bold font-mono text-ink mt-0.5">{p.units_count}</div>
                  </div>
                  <div className="p-2.5 border border-line rounded-xl bg-surface-2/60">
                    <div className="text-[10px] text-muted uppercase font-semibold">Field Cadres</div>
                    <div className="text-sm font-bold font-mono text-forest mt-0.5">{p.teams_ready}</div>
                  </div>
                  <div className="p-2.5 border border-line rounded-xl bg-surface-2/60">
                    <div className="text-[10px] text-muted uppercase font-semibold">Hospitals</div>
                    <div className="text-sm font-bold font-mono text-safe mt-0.5">{p.hospitals_count}</div>
                  </div>
                </div>
              </div>
            </div>

            <div className="pt-3 border-t border-line/60 text-[11px] text-muted flex items-center justify-between">
              <span>Exposed Population:</span>
              <span className="font-bold font-mono text-ink">{p.population_exposed.toLocaleString()}</span>
            </div>
          </SpotlightCard>
        ))}
      </div>
    </div>
  );
}
