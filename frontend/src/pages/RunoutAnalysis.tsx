import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Info, MapPin, RefreshCw, Route, TrendingDown } from "lucide-react";
import { api } from "../lib/api";
import { RiskBadge } from "../components/ui";
import {
  AppleGlassStat,
  DisclosurePill,
  SegmentedControl,
  ShimmerButton,
  SpotlightCard,
} from "../components/aceternity";
import {
  Badge,
  Alert,
  AlertTitle,
  AlertDescription,
} from "../components/shadcn";

interface RunoutProfile {
  zone_id: number;
  zone_code: string;
  zone_name: string;
  district_code: string;
  hazard_index: number;
  hazard_level: "CRITICAL" | "WARNING" | "WATCH" | "SAFE";
  runout: {
    start_elevation_m: number;
    estimated_toe_elevation_m: number;
    fall_height_m: number;
    slope_gradient_deg: number;
    aspect_deg: number;
    flow_direction_deg: number;
    fahrboschung_angle_deg: number;
    max_runout_length_m: number;
    toe_width_m: number;
    affected_area_m2: number;
    runout_hazard_class: string;
    estimated_volume_m3: number;
    downslope_flowline_geojson: any;
    runout_corridor_polygon_geojson: any;
    disclaimer: string;
  };
  threatened_settlements: string[];
  threatened_roads: string[];
}

export default function RunoutAnalysis() {
  const [district, setDistrict] = useState<string>("ALL");
  const [selectedProfile, setSelectedProfile] = useState<RunoutProfile | null>(null);

  const { data, isLoading, refetch } = useQuery<{
    count: number;
    runout_profiles: RunoutProfile[];
    methodology: string;
    validation_status: string;
  }>({
    queryKey: ["runout-profiles", district],
    queryFn: () =>
      api(
        `/api/v1/runout/zones${district !== "ALL" ? `?district_code=${district}` : ""}`
      ),
  });

  const profiles = data?.runout_profiles ?? [];
  const current = selectedProfile || (profiles.length > 0 ? profiles[0] : null);

  return (
    <div className="space-y-6">
      {/* Header and Disclosures */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 pb-2 border-b border-line">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="flex items-center gap-1.5 text-[11px] font-semibold text-warning bg-warning/10 border border-warning/25 px-2.5 py-0.5 rounded-full">
              <TrendingDown size={12} />
              Empirical Fahrböschung Kinematics
            </span>
            <DisclosurePill
              text="Heim Travel-Angle & Corominas Volume-Dispersal Formulation"
              tooltip="Outputs depict kinetic energy dissipation corridors and indicative debris reach based on digital elevation gradient and apparent friction coefficient."
            />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-ink">
            Landslide Runout & Debris Impact Zone Analysis
          </h1>
          <p className="text-xs text-muted mt-0.5">
            Physical slope geometry modeling using empirical travel-angle (Fahrböschung) and volume-energy relationships to estimate potential downslope runout envelopes.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <ShimmerButton
            variant="secondary"
            onClick={() => refetch()}
            className="text-xs"
          >
            <RefreshCw size={13} className={isLoading ? "animate-spin" : ""} />
            Sync DEM Slopes
          </ShimmerButton>
        </div>
      </div>

      {/* District Segmented Controller */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <SegmentedControl
          options={[
            { value: "ALL", label: "Statewide (All Profiles)" },
            { value: "AS-KMR", label: "Kamrup Metro (Assam)" },
            { value: "ML-EKH", label: "East Khasi Hills (Meghalaya)" },
            { value: "MZ-AIZ", label: "Aizawl (Mizoram)" },
          ]}
          value={district}
          onChange={(val) => {
            setDistrict(val);
            setSelectedProfile(null);
          }}
        />
        <div className="text-[11px] text-muted">
          Active Slopes Evaluated: <strong className="text-ink font-mono">{profiles.length}</strong>
        </div>
      </div>

      {/* Operational Safety Advisory Banner */}
      <Alert variant="warning" className="rounded-2xl border-warning/30 bg-surface-2/80 dark:bg-surface-2/50 backdrop-blur-md">
        <div className="space-y-1">
          <AlertTitle className="text-xs font-semibold text-ink">
            Operational Safety Advisory — Indicative Kinematic Envelope
          </AlertTitle>
          <AlertDescription className="text-xs text-muted leading-relaxed">
            {data?.validation_status ??
              "ESTIMATED SCENARIOS — REQUIRES EXPERT GEOTECHNICAL VALIDATION. Outputs depict potential energy envelopes, not deterministic failure boundaries."}
          </AlertDescription>
        </div>
      </Alert>

      {/* Runout Profiles Grid & Detail Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Slope Units List */}
        <SpotlightCard className="p-4">
          <div className="text-xs font-bold text-ink uppercase tracking-wider mb-3 pb-2 border-b border-line flex items-center justify-between">
            <span>Monitored Slopes</span>
            <span className="text-[10px] text-muted font-mono">{profiles.length} units</span>
          </div>

          <div className="space-y-2.5 max-h-[560px] overflow-y-auto pr-1">
            {profiles.map((p) => {
              const isSelected = current?.zone_id === p.zone_id;
              return (
                <div
                  key={p.zone_id}
                  onClick={() => setSelectedProfile(p)}
                  className={`p-3.5 rounded-2xl border text-xs cursor-pointer transition-all duration-200 ${
                    isSelected
                      ? "bg-forest/10 border-forest text-ink shadow-sm"
                      : "bg-surface-2/70 dark:bg-surface-2/40 border-line hover:border-forest/40"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-ink truncate">{p.zone_name}</span>
                    <RiskBadge level={p.hazard_level} index={p.hazard_index} />
                  </div>
                  <div className="text-[11px] text-muted mt-1 font-mono">
                    Unit: {p.zone_code} • {p.district_code}
                  </div>
                  <div className="mt-2.5 flex items-center justify-between text-[11px] pt-2 border-t border-line/60">
                    <span className="text-muted">Runout Hazard Class:</span>
                    <Badge variant={p.runout.runout_hazard_class === "EXTREME" || p.runout.runout_hazard_class === "HIGH" ? "destructive" : "warning"}>
                      {p.runout.runout_hazard_class}
                    </Badge>
                  </div>
                </div>
              );
            })}
          </div>
        </SpotlightCard>

        {/* Center & Right: Selected Slope Geometry & Physics Breakdown */}
        <div className="lg:col-span-2 space-y-6">
          {current ? (
            <>
              {/* Physics Apple Glass Stat Cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <AppleGlassStat
                  label="Max Runout Reach (L)"
                  value={`${current.runout.max_runout_length_m} m`}
                  delta="Downslope reach"
                  deltaType="negative"
                />
                <AppleGlassStat
                  label="Travel Angle (α)"
                  value={`${current.runout.fahrboschung_angle_deg}°`}
                  delta="Fahrböschung line"
                  deltaType="neutral"
                />
                <AppleGlassStat
                  label="Total Fall Height (H)"
                  value={`${current.runout.fall_height_m} m`}
                  delta="Crest to toe drop"
                  deltaType="neutral"
                />
                <AppleGlassStat
                  label="Corridor Footprint"
                  value={`${(current.runout.affected_area_m2 / 1000.0).toFixed(1)}k m²`}
                  delta="Fan deposition area"
                  deltaType="positive"
                />
              </div>

              {/* Terrain & Cross-Section Inspector */}
              <SpotlightCard>
                <div className="flex items-center justify-between pb-3 mb-3 border-b border-line">
                  <div className="flex items-center gap-2">
                    <div className="p-2 rounded-xl bg-forest-soft text-forest">
                      <TrendingDown size={16} />
                    </div>
                    <div>
                      <h3 className="font-bold text-xs uppercase tracking-wider text-ink">
                        Runout Trajectory Profile: {current.zone_name}
                      </h3>
                      <p className="text-[11px] text-muted">
                        Slope gradient, aspect direction, and downslope channel parameters
                      </p>
                    </div>
                  </div>
                </div>

                <div className="space-y-4 text-xs">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 p-3.5 bg-surface-2/70 dark:bg-surface-2/40 rounded-2xl border border-line">
                    <div>
                      <span className="text-muted text-[10px] uppercase font-semibold">Crest Elevation</span>
                      <div className="font-bold text-sm font-mono text-ink mt-0.5">{current.runout.start_elevation_m} m ASL</div>
                    </div>
                    <div>
                      <span className="text-muted text-[10px] uppercase font-semibold">Estimated Toe</span>
                      <div className="font-bold text-sm font-mono text-ink mt-0.5">{current.runout.estimated_toe_elevation_m} m ASL</div>
                    </div>
                    <div>
                      <span className="text-muted text-[10px] uppercase font-semibold">Slope Gradient</span>
                      <div className="font-bold text-sm font-mono text-warning mt-0.5">{current.runout.slope_gradient_deg}°</div>
                    </div>
                    <div>
                      <span className="text-muted text-[10px] uppercase font-semibold">Aspect Flow</span>
                      <div className="font-bold text-sm font-mono text-ink mt-0.5">{current.runout.flow_direction_deg}° (Downslope)</div>
                    </div>
                  </div>

                  {/* Threatened Infrastructure */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="p-3.5 bg-surface-2/70 dark:bg-surface-2/40 rounded-2xl border border-line space-y-2">
                      <span className="font-bold text-ink flex items-center gap-1.5 text-[11px] uppercase tracking-wider">
                        <MapPin size={13} className="text-critical" /> Threatened Downslope Settlements
                      </span>
                      {current.threatened_settlements.length === 0 ? (
                        <div className="text-muted text-[11px]">No formal settlements in immediate runout fan.</div>
                      ) : (
                        current.threatened_settlements.map((s, idx) => (
                          <div key={idx} className="p-2.5 bg-critical/5 border border-critical/20 rounded-xl font-medium text-ink">
                            {s}
                          </div>
                        ))
                      )}
                    </div>

                    <div className="p-3.5 bg-surface-2/70 dark:bg-surface-2/40 rounded-2xl border border-line space-y-2">
                      <span className="font-bold text-ink flex items-center gap-1.5 text-[11px] uppercase tracking-wider">
                        <Route size={13} className="text-warning" /> Lifeline Corridors in Trajectory
                      </span>
                      {current.threatened_roads.length === 0 ? (
                        <div className="text-muted text-[11px]">No arterial highway intersects this debris flowline.</div>
                      ) : (
                        current.threatened_roads.map((r, idx) => (
                          <div key={idx} className="p-2.5 bg-warning/5 border border-warning/20 rounded-xl font-medium text-ink">
                            {r}
                          </div>
                        ))
                      )}
                    </div>
                  </div>

                  <div className="p-3.5 bg-surface-2/80 dark:bg-surface-2/50 backdrop-blur-md rounded-2xl border border-line text-[11px] text-muted flex items-start gap-2.5">
                    <Info size={15} className="text-forest shrink-0 mt-0.5" />
                    <span className="leading-relaxed">
                      Methodology: <strong>{data?.methodology}</strong>. This scenario represents an indicative debris dispersal envelope.
                      Evacuation perimeters require numerical 2D shallow-water modeling and ground geotechnical verification.
                    </span>
                  </div>
                </div>
              </SpotlightCard>
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}
