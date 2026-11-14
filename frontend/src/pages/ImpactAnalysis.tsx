import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { AlertOctagon, Compass, Play, RotateCcw, Route } from "lucide-react";
import { api } from "../lib/api";
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
  AlertDescription,
} from "../components/shadcn";

interface ImpactSummary {
  district_code: string;
  high_risk_zones_count: number;
  impacted_road_segments_count: number;
  total_exposed_population: number;
  emergency_facilities_active: number;
  hospitals_ready: number;
  shelters_ready: number;
  status_notice: string;
}

interface BlockageSimulationResult {
  district_code: string;
  blocked_segments_evaluated: number[];
  total_isolated_settlements: number;
  total_exposed_population: number;
  isolated_settlements: Array<{
    id: number;
    name: string;
    population: number;
    blocked_corridor: string;
    isolation_severity: string;
    alternative_route_distance_km: number;
    helipad_or_dropzone_available: boolean;
  }>;
  connected_settlements_sample: Array<{
    id: number;
    name: string;
    population: number;
    distance_to_hq_km: number;
  }>;
  alternative_emergency_route: {
    alternative_available: boolean;
    original_direct_distance_km: number;
    detour_distance_km: number;
    estimated_transit_minutes: number;
    avoided_blockages: string[];
    route_description: string;
    clearance_recommendation: string;
    data_notice: string;
  };
}

export default function ImpactAnalysis() {
  const [district, setDistrict] = useState<string>("AS-KMR");
  const [selectedBlockedSegments, setSelectedBlockedSegments] = useState<number[]>([1, 2]);

  const { data: summary, isLoading: isSummaryLoading } = useQuery<ImpactSummary>({
    queryKey: ["impact-summary", district],
    queryFn: () => api(`/api/v1/impact/summary?district_code=${district}`),
  });

  const simulateMutation = useMutation<BlockageSimulationResult, Error, number[]>({
    mutationFn: (segmentIds: number[]) =>
      api("/api/v1/impact/simulate-blockage", {
        method: "POST",
        body: JSON.stringify({
          district_code: district,
          blocked_segment_ids: segmentIds,
        }),
      }),
  });

  const runSimulation = () => {
    simulateMutation.mutate(selectedBlockedSegments);
  };

  const toggleSegment = (id: number) => {
    setSelectedBlockedSegments((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const simData = simulateMutation.data;

  return (
    <div className="space-y-6">
      {/* Header and Methodological Disclosures */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 pb-2 border-b border-line">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="flex items-center gap-1.5 text-[11px] font-semibold text-primary bg-primary/10 border border-primary/25 px-2.5 py-0.5 rounded-full">
              <Route size={12} />
              Graph Connectivity Engine
            </span>
            <DisclosurePill
              text="Dijkstra Shortest Path & Cut-Vertex Isolation Algorithm"
              tooltip="Settlement connectivity is analyzed dynamically using road network topologies to identify bridges and highway segments whose failure severs vehicular access."
            />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-ink">
            Impact Analysis Engine
          </h1>
          <p className="text-xs text-muted mt-0.5">
            Geospatial consequence modeling, road network graph connectivity analysis, isolated village detection, and population exposure estimation.
          </p>
        </div>

      </div>

      {/* District Selector */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <SegmentedControl
          options={[
            { value: "AS-KMR", label: "Kamrup Metropolitan (Assam)" },
            { value: "ML-EKH", label: "East Khasi Hills (Meghalaya)" },
            { value: "MZ-AIZ", label: "Aizawl (Mizoram)" },
          ]}
          value={district}
          onChange={(val) => {
            setDistrict(val);
            simulateMutation.reset();
          }}
        />
        <div className="text-[11px] text-muted">
          District Headquarters: <strong className="text-ink">DC Office Command Node</strong>
        </div>
      </div>

      {/* Exposure Summary Apple Glass Stat Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <AppleGlassStat
          label="Exposed Population"
          value={isSummaryLoading ? "—" : (summary?.total_exposed_population ?? 0).toLocaleString()}
          delta="Across high-hazard units"
          deltaType="negative"
        />
        <AppleGlassStat
          label="Threatened Road Spans"
          value={isSummaryLoading ? "—" : summary?.impacted_road_segments_count ?? 0}
          delta="Cut-slope road corridors"
          deltaType="negative"
        />
        <AppleGlassStat
          label="Operational Hospitals"
          value={isSummaryLoading ? "—" : summary?.hospitals_ready ?? 0}
          delta="Medical trauma ready"
          deltaType="positive"
        />
        <AppleGlassStat
          label="Designated Shelters"
          value={isSummaryLoading ? "—" : summary?.shelters_ready ?? 0}
          delta="Verified capacity active"
          deltaType="positive"
        />
      </div>

      {/* Interactive Road Network Blockage Simulator */}
      <SpotlightCard>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 mb-4 border-b border-line gap-3">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-forest-soft text-forest">
              <Route size={18} />
            </div>
            <div>
              <h2 className="font-bold text-sm text-ink">
                Road Network Blockage & Settlement Isolation Simulator
              </h2>
              <p className="text-xs text-muted">
                Graph-based connectivity algorithm: hypothetically block road segments to calculate disconnected settlements
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setSelectedBlockedSegments([])}
              className="px-3 py-1.5 text-xs font-medium rounded-xl border border-line bg-surface-2 hover:bg-surface text-muted hover:text-ink transition flex items-center gap-1.5"
            >
              <RotateCcw size={12} /> Reset
            </button>
            <ShimmerButton
              onClick={runSimulation}
              disabled={simulateMutation.isPending}
              variant="primary"
            >
              <Play size={12} />
              {simulateMutation.isPending ? "Calculating Isolation Graph..." : "Calculate Network Isolation"}
            </ShimmerButton>
          </div>
        </div>

        <div className="space-y-4">
          <div className="text-xs text-muted">
            Toggle road segments below to simulate hypothetical landslide blockage points along the mountain transport corridor:
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2.5">
            {[
              { id: 1, name: "NH-27 Khanapara - Jorabat Corridor", len: 4.8 },
              { id: 2, name: "Sonapur Hill Cutting Bypass", len: 3.2 },
              { id: 3, name: "Guwahati-Shillong Ridge Highway KM 14", len: 6.5 },
              { id: 4, name: "Narakasur Hill Link Arterial", len: 2.1 },
              { id: 5, name: "Deepor Beel Peripheral Access", len: 5.4 },
              { id: 6, name: "Amiya Nagar Hill Slopes Road", len: 1.8 },
            ].map((seg) => {
              const isBlocked = selectedBlockedSegments.includes(seg.id);
              return (
                <button
                  key={seg.id}
                  onClick={() => toggleSegment(seg.id)}
                  className={`p-3 rounded-2xl border text-left transition-all duration-200 ${
                    isBlocked
                      ? "bg-critical/10 border-critical/50 text-ink shadow-sm"
                      : "bg-surface-2/70 dark:bg-surface-2/40 border-line text-muted hover:border-forest/40 hover:text-ink"
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[11px] font-mono font-bold">Seg #{seg.id}</span>
                    <span
                      className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded-full ${
                        isBlocked
                          ? "bg-critical text-white"
                          : "bg-surface-3 text-muted"
                      }`}
                    >
                      {isBlocked ? "BLOCKED" : "OPEN"}
                    </span>
                  </div>
                  <div className="text-xs font-semibold text-ink truncate">{seg.name}</div>
                  <div className="text-[10px] text-muted font-mono mt-0.5">{seg.len} km length</div>
                </button>
              );
            })}
          </div>

          {/* Simulation Output Area */}
          {simData ? (
            <div className="mt-6 space-y-6 pt-5 border-t border-line">
              <div className="flex flex-wrap items-center justify-between gap-3 bg-surface-2/80 dark:bg-surface-2/50 backdrop-blur-md p-4 rounded-2xl border border-line">
                <div>
                  <span className="text-[10px] text-forest uppercase tracking-wider font-bold">
                    Graph Cut Simulation Output
                  </span>
                  <h3 className="text-sm font-bold text-ink mt-0.5">
                    {simData.total_isolated_settlements} Settlement(s) Disconnected from District Headquarters
                  </h3>
                </div>
                <div className="flex items-center gap-5 text-xs">
                  <div>
                    <span className="text-muted">Affected Population: </span>
                    <strong className="text-critical tabular-nums font-bold">
                      {simData.total_exposed_population.toLocaleString()}
                    </strong>
                  </div>
                  <div>
                    <span className="text-muted">Detour Required: </span>
                    <strong className="text-warning tabular-nums font-bold">
                      +{simData.alternative_emergency_route.detour_distance_km} km
                    </strong>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Isolated Settlements List */}
                <div className="space-y-3">
                  <h4 className="text-xs font-bold text-muted uppercase tracking-wider flex items-center gap-1.5">
                    <AlertOctagon size={14} className="text-critical" />
                    Isolated Settlements Requiring Emergency Supply Corridors
                  </h4>
                  <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
                    {simData.isolated_settlements.length === 0 ? (
                      <div className="text-xs text-muted p-4 bg-surface-2 rounded-2xl border border-line text-center">
                        No settlements completely cut off under this blockage configuration.
                      </div>
                    ) : (
                      simData.isolated_settlements.map((s) => (
                        <div
                          key={s.id}
                          className="p-3.5 bg-critical/5 border border-critical/25 rounded-2xl flex items-center justify-between"
                        >
                          <div>
                            <div className="text-xs font-bold text-ink">{s.name}</div>
                            <div className="text-[11px] text-muted mt-0.5">
                              Blocked at: <span className="font-semibold text-ink">{s.blocked_corridor}</span>
                            </div>
                            <div className="flex items-center gap-1.5 mt-1.5">
                              <Badge variant="destructive">{s.isolation_severity}</Badge>
                              {s.helipad_or_dropzone_available ? (
                                <Badge variant="success">Air-Drop Viable</Badge>
                              ) : (
                                <Badge variant="secondary">Ground Relief Only</Badge>
                              )}
                            </div>
                          </div>
                          <div className="text-right shrink-0">
                            <span className="text-xs font-bold text-critical tabular-nums font-mono">
                              {s.population.toLocaleString()}
                            </span>
                            <div className="text-[10px] text-muted font-medium">Residents</div>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                {/* Alternative Bypass Route Card */}
                <div className="space-y-3">
                  <h4 className="text-xs font-bold text-muted uppercase tracking-wider flex items-center gap-1.5">
                    <Compass size={14} className="text-forest" />
                    AI Recommended Alternative Emergency Route
                  </h4>
                  <div className="p-4 bg-surface-2/80 dark:bg-surface-2/50 backdrop-blur-md border border-line rounded-2xl space-y-3 text-xs">
                    <div className="flex items-center justify-between border-b border-line pb-2.5">
                      <span className="text-muted">Route Corridor</span>
                      <span className="font-semibold text-ink">
                        {simData.alternative_emergency_route.route_description}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-3 text-center py-1">
                      <div className="p-3 bg-surface-3/70 dark:bg-surface-3/40 rounded-xl border border-line">
                        <div className="text-[10px] text-muted uppercase font-semibold">Direct Distance</div>
                        <div className="text-sm font-bold font-mono text-ink mt-0.5">
                          {simData.alternative_emergency_route.original_direct_distance_km} km
                        </div>
                      </div>
                      <div className="p-3 bg-warning/10 text-warning rounded-xl border border-warning/20">
                        <div className="text-[10px] text-warning/80 uppercase font-semibold">Detour Route</div>
                        <div className="text-sm font-bold font-mono mt-0.5">
                          {simData.alternative_emergency_route.detour_distance_km} km (~{simData.alternative_emergency_route.estimated_transit_minutes} min)
                        </div>
                      </div>
                    </div>
                    <div>
                      <span className="text-muted block text-[11px] font-semibold">SOP Clearance Directive:</span>
                      <p className="text-xs text-ink leading-relaxed mt-0.5">
                        {simData.alternative_emergency_route.clearance_recommendation}
                      </p>
                    </div>
                    <Alert variant="info" className="p-3 text-[11px] rounded-xl border border-line/60">
                      <AlertDescription>
                        Notice: {simData.alternative_emergency_route.data_notice}
                      </AlertDescription>
                    </Alert>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="p-8 text-center text-xs text-muted border border-dashed border-line rounded-2xl">
              Select one or more road segments above and click <strong>Calculate Network Isolation</strong> to compute cut-vertex isolation and alternative emergency detours.
            </div>
          )}
        </div>
      </SpotlightCard>
    </div>
  );
}
