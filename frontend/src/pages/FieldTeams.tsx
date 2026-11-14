import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Bot, Briefcase, Phone, RefreshCw, Sparkles, Users } from "lucide-react";
import { api } from "../lib/api";
import {
  DisclosurePill,
  SegmentedControl,
  ShimmerButton,
  SpotlightCard,
} from "../components/aceternity";
import {
  Badge,
  Progress,
} from "../components/shadcn";

interface FieldTeam {
  id: number;
  team_code: string;
  name: string;
  district_code: string;
  leader_name: string;
  leader_phone: string;
  specialization: string;
  base_lat: number;
  base_lon: number;
  status: "AVAILABLE" | "DISPATCHED" | "ON_SITE" | "RESTING" | "OFF_DUTY";
  member_count: number;
  current_active_assignments: number;
  equipment: string[];
}

interface RankedTeam {
  team_id: number;
  team_code: string;
  team_name: string;
  specialization: string;
  status: string;
  estimated_distance_km: number;
  estimated_transit_min: number;
  road_accessible: boolean;
  score_breakdown: {
    distance_score: number;
    road_access_score: number;
    skill_match_score: number;
    workload_score: number;
    composite_score: number;
  };
  composite_score: number;
  recommendation_rationale: string;
  rank: number;
}

export default function FieldTeams() {
  const [district, setDistrict] = useState<string>("ALL");
  const [simIncident, setSimIncident] = useState({
    hazard_type: "SLOPE_MOVEMENT",
    priority: "P1",
    lat: 26.152,
    lon: 91.775,
    district_code: "AS-KMR",
  });

  const { data: teamsData, isLoading, refetch } = useQuery<{ count: number; teams: FieldTeam[] }>({
    queryKey: ["field-teams", district],
    queryFn: () =>
      api(`/api/v1/teams${district !== "ALL" ? `?district_code=${district}` : ""}`),
  });

  const optimizerMutation = useMutation<{ ranked_recommendations: RankedTeam[]; recommended_team: RankedTeam }>({
    mutationFn: () =>
      api("/api/v1/teams/optimize", {
        method: "POST",
        body: JSON.stringify(simIncident),
      }),
  });

  const teams = teamsData?.teams ?? [];

  return (
    <div className="space-y-6">
      {/* Header and Disclosures */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 pb-2 border-b border-line">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="flex items-center gap-1.5 text-[11px] font-semibold text-forest bg-forest-soft border border-forest/25 px-2.5 py-0.5 rounded-full">
              <Users size={12} />
              Cadre Readiness & Allocation Engine
            </span>
            <DisclosurePill
              text="Multi-Criteria Decision Analysis (MCDA) + Explainable Dispatch"
              tooltip="Ranks teams based on geographical proximity, road access, geotechnical specialization, and fatigue workload balance. Fully overridable by incident commander."
            />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-ink">
            Field Teams & AI Response Optimizer
          </h1>
          <p className="text-xs text-muted mt-0.5">
            Real-time field cadre live status, active assignment workloads, and multi-criteria explainable AI team dispatch optimizer.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <ShimmerButton
            variant="secondary"
            onClick={() => refetch()}
            className="text-xs"
          >
            <RefreshCw size={13} className={isLoading ? "animate-spin" : ""} />
            Sync Teams
          </ShimmerButton>
        </div>
      </div>

      {/* District Segmented Controller */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <SegmentedControl
          options={[
            { value: "ALL", label: "Statewide Cadre" },
            { value: "AS-KMR", label: "Kamrup Metro" },
            { value: "ML-EKH", label: "East Khasi Hills" },
            { value: "MZ-AIZ", label: "Aizawl" },
          ]}
          value={district}
          onChange={setDistrict}
        />
        <div className="text-[11px] text-muted">
          Active Responders Registered: <strong className="text-ink font-mono">{teams.length} teams</strong>
        </div>
      </div>

      {/* Cadre Roster Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {teams.map((t) => (
          <SpotlightCard key={t.id} className="p-4 flex flex-col justify-between space-y-3">
            <div>
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-bold text-forest">{t.team_code}</span>
                <Badge
                  variant={t.status === "AVAILABLE" ? "success" : "warning"}
                  className="font-mono text-[9px] uppercase tracking-wide"
                >
                  {t.status}
                </Badge>
              </div>
              <h3 className="text-sm font-bold text-ink mt-1.5 truncate">{t.name}</h3>
              <div className="text-[11px] text-muted capitalize font-medium">
                {t.specialization.replace(/_/g, " ").toLowerCase()}
              </div>

              <div className="mt-3 space-y-1.5 text-xs text-muted">
                <div className="flex items-center gap-1.5">
                  <Users size={13} className="text-muted/80" />
                  <span>Leader: <strong className="text-ink">{t.leader_name}</strong></span>
                </div>
                <div className="flex items-center gap-1.5">
                  <Phone size={13} className="text-muted/80" />
                  <span className="font-mono text-[11px]">{t.leader_phone}</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <Briefcase size={13} className="text-muted/80" />
                  <span>Active Backlog: <strong className="text-ink">{t.current_active_assignments} mission(s)</strong></span>
                </div>
              </div>
            </div>

            <div className="pt-2.5 border-t border-line/60 text-[10px] text-muted font-mono truncate">
              Equipped: {t.equipment?.join(", ") || "Standard field kit"}
            </div>
          </SpotlightCard>
        ))}
      </div>

      {/* AI Team Allocation Optimizer */}
      <SpotlightCard>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 mb-4 border-b border-line gap-3">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-forest-soft text-forest">
              <Bot size={18} />
            </div>
            <div>
              <h2 className="font-bold text-sm text-ink">
                Smart Response Optimizer — Explainable AI Team Dispatch
              </h2>
              <p className="text-xs text-muted">
                Multi-criteria MCDA algorithm evaluates distance, road availability, skill set, and workload
              </p>
            </div>
          </div>

          <ShimmerButton
            onClick={() => optimizerMutation.mutate()}
            disabled={optimizerMutation.isPending}
            variant="primary"
          >
            <Sparkles size={13} />
            {optimizerMutation.isPending ? "Ranking Cadres..." : "Run AI Allocation"}
          </ShimmerButton>
        </div>

        <div className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
            <div>
              <label className="block text-[11px] text-muted font-medium mb-1">Target Hazard</label>
              <select
                value={simIncident.hazard_type}
                onChange={(e) => setSimIncident({ ...simIncident, hazard_type: e.target.value })}
                className="w-full bg-surface-2/80 dark:bg-surface-2/50 border border-line rounded-xl p-2 text-ink text-xs focus:outline-none"
              >
                <option value="SLOPE_MOVEMENT">Slope Movement</option>
                <option value="ROCKFALL">Rockfall</option>
                <option value="DEBRIS_FLOW">Debris Flow</option>
                <option value="SUBSIDENCE">Subsidence</option>
              </select>
            </div>
            <div>
              <label className="block text-[11px] text-muted font-medium mb-1">Priority Level</label>
              <select
                value={simIncident.priority}
                onChange={(e) => setSimIncident({ ...simIncident, priority: e.target.value })}
                className="w-full bg-surface-2/80 dark:bg-surface-2/50 border border-line rounded-xl p-2 text-ink text-xs focus:outline-none"
              >
                <option value="P1">P1 — Immediate Life-Safety</option>
                <option value="P2">P2 — Urgent Infrastructure</option>
                <option value="P3">P3 — Monitor</option>
              </select>
            </div>
            <div>
              <label className="block text-[11px] text-muted font-medium mb-1">Incident Latitude</label>
              <input
                type="number"
                step="0.001"
                value={simIncident.lat}
                onChange={(e) => setSimIncident({ ...simIncident, lat: parseFloat(e.target.value) })}
                className="w-full bg-surface-2/80 dark:bg-surface-2/50 border border-line rounded-xl p-2 text-ink text-xs font-mono focus:outline-none"
              >
              </input>
            </div>
            <div>
              <label className="block text-[11px] text-muted font-medium mb-1">Incident Longitude</label>
              <input
                type="number"
                step="0.001"
                value={simIncident.lon}
                onChange={(e) => setSimIncident({ ...simIncident, lon: parseFloat(e.target.value) })}
                className="w-full bg-surface-2/80 dark:bg-surface-2/50 border border-line rounded-xl p-2 text-ink text-xs font-mono focus:outline-none"
              >
              </input>
            </div>
          </div>

          {optimizerMutation.data ? (
            <div className="mt-5 space-y-3 pt-4 border-t border-line">
              <h4 className="text-xs font-bold text-muted uppercase tracking-wider">
                Ranked Field Team Recommendations (Explainable MCDA Breakdown)
              </h4>
              <div className="space-y-3">
                {optimizerMutation.data.ranked_recommendations.map((rec) => (
                  <div
                    key={rec.team_id}
                    className={`p-4 rounded-2xl border text-xs space-y-2.5 transition duration-200 ${
                      rec.rank === 1
                        ? "bg-forest/10 border-forest text-ink shadow-sm"
                        : "bg-surface-2/70 dark:bg-surface-2/40 border-line"
                    }`}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-sm text-ink">
                          #{rec.rank} — {rec.team_name}
                        </span>
                        <span className="font-mono text-[11px] text-muted">[{rec.team_code}]</span>
                        {rec.rank === 1 ? (
                          <Badge variant="default" className="text-[9px] bg-forest text-white">
                            AI RECOMMENDED
                          </Badge>
                        ) : null}
                      </div>
                      <div className="text-right">
                        <span className="font-bold text-sm font-mono text-forest">
                          {rec.composite_score} / 100
                        </span>
                        <div className="text-[10px] text-muted">Composite Match</div>
                      </div>
                    </div>

                    <Progress value={rec.composite_score} className="h-1.5" />

                    <p className="text-ink font-medium bg-surface-3/70 dark:bg-surface-3/40 p-2.5 rounded-xl border border-line/50 leading-relaxed">
                      Rationale: {rec.recommendation_rationale}
                    </p>

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-[11px] text-muted">
                      <div>Distance: <strong className="text-ink font-mono">{rec.estimated_distance_km} km</strong></div>
                      <div>Transit: <strong className="text-ink font-mono">~{rec.estimated_transit_min} min</strong></div>
                      <div>Access: <strong className={rec.road_accessible ? "text-safe" : "text-critical"}>{rec.road_accessible ? "Road Open" : "Detour Needed"}</strong></div>
                      <div>Workload: <strong className="text-ink font-mono">{rec.score_breakdown.workload_score}/100</strong></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="text-xs text-muted p-6 bg-surface-2/60 dark:bg-surface-2/30 rounded-2xl text-center border border-dashed border-line">
              Click <strong>Run AI Allocation</strong> above to execute the multi-criteria ranking algorithm and generate transparent deployment reasoning.
            </div>
          )}
        </div>
      </SpotlightCard>
    </div>
  );
}
