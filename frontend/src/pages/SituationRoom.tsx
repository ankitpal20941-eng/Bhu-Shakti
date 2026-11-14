import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  Building2,
  CheckCircle2,
  Clock,
  Hospital,
  MapPin,
  Radio,
  RefreshCw,
  Route,
  ShieldAlert,
} from "lucide-react";
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
  Alert,
  AlertTitle,
  AlertDescription,
} from "../components/shadcn";

interface SituationRoomData {
  active_filter_district: string;
  counts: {
    critical_zones: number;
    warning_zones: number;
    watch_zones: number;
    pending_alert_approvals: number;
    active_field_assignments: number;
    disrupted_road_segments: number;
    operational_facilities: number;
    recent_reports: number;
  };
  critical_zones: Array<{
    id: number;
    code: string;
    name: string;
    district_code: string;
    hazard_index: number;
    hazard_level: "CRITICAL" | "WARNING" | "WATCH" | "SAFE";
    priority_level: string;
  }>;
  warning_zones: Array<{
    id: number;
    code: string;
    name: string;
    district_code: string;
    hazard_index: number;
    hazard_level: "CRITICAL" | "WARNING" | "WATCH" | "SAFE";
    priority_level: string;
  }>;
  pending_alerts: Array<{
    id: number;
    reference: string;
    headline: string;
    severity: string;
    created_at: string;
  }>;
  disrupted_roads: Array<{
    id: number;
    name: string;
    status: string;
    length_km: number;
    status_source: string;
  }>;
  operational_facilities: Array<{
    id: number;
    name: string;
    kind: string;
    district_code: string;
    capacity: number;
    occupancy: number;
  }>;
  recent_reports: Array<{
    id: number;
    hazard_type: string;
    status: string;
    description: string;
    observed_at: string;
  }>;
  telemetry_stream_status: string;
}

export default function SituationRoom() {
  const [district, setDistrict] = useState<string>("ALL");

  const { data, isLoading, refetch } = useQuery<SituationRoomData>({
    queryKey: ["situation-room", district],
    queryFn: () =>
      api(
        `/api/v1/situation-room${district !== "ALL" ? `?district_code=${district}` : ""}`
      ),
    refetchInterval: 15_000,
  });

  const counts = data?.counts;

  return (
    <div className="space-y-6">
      {/* Top Header & Disclosures */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 pb-2 border-b border-line">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="flex items-center gap-1.5 text-[11px] font-semibold text-safe bg-safe/10 border border-safe/25 px-2.5 py-0.5 rounded-full">
              <Radio size={12} className="animate-pulse" />
              Live Telemetry Stream Active
            </span>
            <DisclosurePill
              text="State Disaster Management Authority Directive"
              tooltip="All early warnings and road advisory actions must be formally confirmed by the District Disaster Management Authority (DDMA)."
            />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-ink">
            Emergency Situation Room
          </h1>
          <p className="text-xs text-muted mt-0.5">
            Real-time geospatial hazard matrix, alert approval queues, and lifeline infrastructure status.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <ShimmerButton
            variant="secondary"
            onClick={() => refetch()}
            className="text-xs"
          >
            <RefreshCw size={13} className={isLoading ? "animate-spin" : ""} />
            Sync Feeds
          </ShimmerButton>
        </div>
      </div>

      {/* District Segmented Controller */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <SegmentedControl
          options={[
            { value: "ALL", label: "Statewide (All Pilots)" },
            { value: "AS-KMR", label: "Kamrup Metro (Assam)" },
            { value: "ML-EKH", label: "East Khasi Hills (Meghalaya)" },
            { value: "MZ-AIZ", label: "Aizawl (Mizoram)" },
          ]}
          value={district}
          onChange={setDistrict}
        />
        <div className="text-[11px] text-muted flex items-center gap-2">
          <span>Polling interval: <strong className="text-ink">15s</strong></span>
          <span>•</span>
          <span>Last sync: <strong className="text-ink">{new Date().toLocaleTimeString()}</strong></span>
        </div>
      </div>

      {/* Primary KPI Ribbon - Apple Glass Stat Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3">
        <AppleGlassStat
          label="Critical Zones"
          value={isLoading ? "—" : counts?.critical_zones ?? 0}
          delta="Hazard index ≥ 80"
          deltaType="negative"
        />
        <AppleGlassStat
          label="Warning Zones"
          value={isLoading ? "—" : counts?.warning_zones ?? 0}
          delta="Hazard index 60–79"
          deltaType="negative"
        />
        <AppleGlassStat
          label="Watch Zones"
          value={isLoading ? "—" : counts?.watch_zones ?? 0}
          delta="Hazard index 30–59"
          deltaType="neutral"
        />
        <AppleGlassStat
          label="Pending Alerts"
          value={isLoading ? "—" : counts?.pending_alert_approvals ?? 0}
          delta="Requires DC sign-off"
          deltaType="neutral"
        />
        <AppleGlassStat
          label="Field Teams"
          value={isLoading ? "—" : counts?.active_field_assignments ?? 0}
          delta="On live missions"
          deltaType="positive"
        />
        <AppleGlassStat
          label="Disrupted Roads"
          value={isLoading ? "—" : counts?.disrupted_road_segments ?? 0}
          delta="Blocked corridors"
          deltaType="negative"
        />
        <AppleGlassStat
          label="Shelters Open"
          value={isLoading ? "—" : counts?.operational_facilities ?? 0}
          delta="Designated safe hubs"
          deltaType="positive"
        />
        <AppleGlassStat
          label="Verified Reports"
          value={isLoading ? "—" : counts?.recent_reports ?? 0}
          delta="24h ground reports"
          deltaType="positive"
        />
      </div>

      {/* Main Command Matrix */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Active High-Hazard Slope Units */}
        <div className="space-y-6">
          <SpotlightCard>
            <div className="flex items-center justify-between pb-3 mb-3 border-b border-line">
              <div className="flex items-center gap-2">
                <div className="p-2 rounded-xl bg-critical/10 text-critical">
                  <ShieldAlert size={16} />
                </div>
                <div>
                  <h3 className="font-bold text-xs uppercase tracking-wider text-ink">
                    Active High-Hazard Slopes
                  </h3>
                  <p className="text-[11px] text-muted">
                    Exceeding localized rainfall & slope stability thresholds
                  </p>
                </div>
              </div>
              <span className="text-[11px] font-mono font-semibold px-2 py-0.5 rounded bg-surface-2 border border-line">
                {[...(data?.critical_zones ?? []), ...(data?.warning_zones ?? [])].length} zones
              </span>
            </div>

            <div className="space-y-2.5 max-h-[460px] overflow-y-auto pr-1">
              {isLoading ? (
                <div className="text-xs text-muted py-8 text-center animate-pulse">
                  Querying GSI slope polygons...
                </div>
              ) : [...(data?.critical_zones ?? []), ...(data?.warning_zones ?? [])].length === 0 ? (
                <div className="text-center py-8">
                  <CheckCircle2 size={28} className="mx-auto text-safe/70 mb-2" />
                  <div className="text-xs font-semibold text-ink">No High Hazard Slopes Active</div>
                  <p className="text-[11px] text-muted mt-0.5">All monitored slopes operate below warning thresholds.</p>
                </div>
              ) : (
                [...(data?.critical_zones ?? []), ...(data?.warning_zones ?? [])].map((z) => (
                  <div
                    key={z.id}
                    className="p-3 bg-surface-2/70 dark:bg-surface-2/40 border border-line rounded-xl flex items-center justify-between gap-3 hover:border-forest/40 transition duration-200"
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-xs text-ink truncate">
                          {z.name}
                        </span>
                        <span className="text-[10px] text-muted uppercase font-mono">[{z.district_code}]</span>
                      </div>
                      <div className="text-[11px] text-muted mt-0.5">
                        Priority: <strong className="text-ink">{z.priority_level}</strong> | Code: <span className="font-mono">{z.code}</span>
                      </div>
                    </div>
                    <RiskBadge level={z.hazard_level} index={z.hazard_index} />
                  </div>
                ))
              )}
            </div>
          </SpotlightCard>

          <SpotlightCard>
            <div className="flex items-center justify-between pb-3 mb-3 border-b border-line">
              <div className="flex items-center gap-2">
                <div className="p-2 rounded-xl bg-safe/10 text-safe">
                  <Hospital size={16} />
                </div>
                <div>
                  <h3 className="font-bold text-xs uppercase tracking-wider text-ink">
                    Emergency Facilities Status
                  </h3>
                  <p className="text-[11px] text-muted">
                    Designated safe assembly hubs and district trauma centers
                  </p>
                </div>
              </div>
            </div>

            <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
              {isLoading ? (
                <div className="text-xs text-muted py-6 text-center animate-pulse">Loading facilities...</div>
              ) : (data?.operational_facilities ?? []).map((f) => (
                <div
                  key={f.id}
                  className="p-2.5 bg-surface-2/70 dark:bg-surface-2/40 border border-line rounded-xl flex items-center justify-between"
                >
                  <div className="min-w-0">
                    <div className="text-xs font-semibold text-ink truncate">{f.name}</div>
                    <div className="text-[10px] text-muted uppercase font-mono">
                      {f.kind.replace("_", " ")} • {f.district_code}
                    </div>
                  </div>
                  <div className="text-right shrink-0">
                    <span className="text-xs font-bold text-safe tabular-nums">
                      {f.capacity - f.occupancy} beds open
                    </span>
                    <div className="text-[10px] text-muted font-mono">{f.occupancy} / {f.capacity} occupied</div>
                  </div>
                </div>
              ))}
            </div>
          </SpotlightCard>
        </div>

        {/* Center Column: Alert Approval Queue & Disrupted Corridors */}
        <div className="space-y-6">
          <SpotlightCard>
            <div className="flex items-center justify-between pb-3 mb-3 border-b border-line">
              <div className="flex items-center gap-2">
                <div className="p-2 rounded-xl bg-warning/10 text-warning">
                  <AlertTriangle size={16} />
                </div>
                <div>
                  <h3 className="font-bold text-xs uppercase tracking-wider text-ink">
                    Alert Approvals Queue
                  </h3>
                  <p className="text-[11px] text-muted">
                    Early warning bulletins awaiting District Magistrate digital authorization
                  </p>
                </div>
              </div>
              <span className="text-[11px] font-mono font-bold px-2 py-0.5 rounded bg-warning/10 text-warning border border-warning/30">
                {data?.pending_alerts?.length ?? 0} Pending
              </span>
            </div>

            <div className="space-y-3">
              {(data?.pending_alerts ?? []).length === 0 ? (
                <div className="text-center py-8">
                  <CheckCircle2 size={32} className="mx-auto text-safe/80 mb-2" />
                  <div className="text-xs font-semibold text-ink">Queue Clear</div>
                  <p className="text-[11px] text-muted mt-0.5">All issued alerts have been officially authorized and broadcast.</p>
                </div>
              ) : (
                data?.pending_alerts.map((a) => (
                  <div
                    key={a.id}
                    className="p-3.5 bg-warning/5 border border-warning/30 rounded-xl space-y-2"
                  >
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-mono font-bold text-warning">{a.reference}</span>
                      <span className="text-[10px] text-muted flex items-center gap-1 font-mono">
                        <Clock size={11} /> {new Date(a.created_at).toLocaleTimeString()}
                      </span>
                    </div>
                    <p className="text-xs font-medium text-ink leading-relaxed">{a.headline}</p>
                    <div className="pt-1 flex items-center gap-2">
                      <a
                        href="/alerts"
                        className="w-full text-center py-2 px-3 text-xs font-semibold rounded-xl bg-forest text-white shadow-md shadow-forest/20 hover:brightness-105 transition"
                      >
                        Review & Authorize Publication
                      </a>
                    </div>
                  </div>
                ))
              )}
            </div>
          </SpotlightCard>

          <SpotlightCard>
            <div className="flex items-center justify-between pb-3 mb-3 border-b border-line">
              <div className="flex items-center gap-2">
                <div className="p-2 rounded-xl bg-critical/10 text-critical">
                  <Route size={16} />
                </div>
                <div>
                  <h3 className="font-bold text-xs uppercase tracking-wider text-ink">
                    Disrupted Lifeline Corridors
                  </h3>
                  <p className="text-[11px] text-muted">
                    National & state highways blocked or under high failure risk
                  </p>
                </div>
              </div>
            </div>

            <div className="space-y-2 max-h-[320px] overflow-y-auto pr-1">
              {(data?.disrupted_roads ?? []).length === 0 ? (
                <div className="text-center py-8">
                  <CheckCircle2 size={28} className="mx-auto text-safe/70 mb-2" />
                  <div className="text-xs font-semibold text-ink">All Corridors Open</div>
                  <p className="text-[11px] text-muted mt-0.5">No reported roadblocks or high-failure segments.</p>
                </div>
              ) : (
                data?.disrupted_roads.map((r) => (
                  <div
                    key={r.id}
                    className="p-3 bg-surface-2/70 dark:bg-surface-2/40 border border-line rounded-xl flex items-center justify-between"
                  >
                    <div className="min-w-0">
                      <div className="text-xs font-semibold text-ink truncate">{r.name}</div>
                      <div className="text-[10px] text-muted font-mono">
                        Span: {r.length_km} km | Source: {r.status_source}
                      </div>
                    </div>
                    <span
                      className={`text-[10px] font-bold font-mono px-2 py-0.5 rounded-full border uppercase ${
                        r.status === "BLOCKED"
                          ? "bg-critical/15 text-critical border-critical/40"
                          : "bg-warning/15 text-warning border-warning/40"
                      }`}
                    >
                      {r.status}
                    </span>
                  </div>
                ))
              )}
            </div>
          </SpotlightCard>
        </div>

        {/* Right Column: Live Incident Stream & SOP Banner */}
        <div className="space-y-6">
          <SpotlightCard>
            <div className="flex items-center justify-between pb-3 mb-3 border-b border-line">
              <div className="flex items-center gap-2">
                <div className="p-2 rounded-xl bg-forest-soft text-forest">
                  <MapPin size={16} />
                </div>
                <div>
                  <h3 className="font-bold text-xs uppercase tracking-wider text-ink">
                    Field Telemetry & Citizen Reports
                  </h3>
                  <p className="text-[11px] text-muted">
                    Ground-truth mobile reports verified by field geologists
                  </p>
                </div>
              </div>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-surface-2 border border-line">
                Last 24h
              </span>
            </div>

            <div className="space-y-3 max-h-[460px] overflow-y-auto pr-1">
              {(data?.recent_reports ?? []).length === 0 ? (
                <div className="text-xs text-muted py-8 text-center">No ground reports recorded today.</div>
              ) : (
                (data?.recent_reports ?? []).map((rep) => (
                  <div
                    key={rep.id}
                    className="p-3 bg-surface-2/70 dark:bg-surface-2/40 border border-line rounded-xl space-y-1.5"
                  >
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-bold text-forest text-xs">
                        {rep.hazard_type.replace("_", " ")}
                      </span>
                      <span
                        className={`text-[10px] font-bold font-mono px-2 py-0.5 rounded-full border ${
                          rep.status === "VERIFIED"
                            ? "bg-safe/10 text-safe border-safe/30"
                            : "bg-surface-3 text-muted border-line"
                        }`}
                      >
                        {rep.status}
                      </span>
                    </div>
                    <p className="text-xs text-muted leading-relaxed line-clamp-2">{rep.description}</p>
                    <div className="text-[10px] text-muted/70 font-mono">
                      Observed: {new Date(rep.observed_at).toLocaleString()}
                    </div>
                  </div>
                ))
              )}
            </div>
          </SpotlightCard>

          {/* SOP Operational Authority Banner */}
          <Alert variant="default" className="border-line/80 bg-surface-2/80 dark:bg-surface-2/50 backdrop-blur-md">
            <div className="space-y-1">
              <AlertTitle className="flex items-center gap-1.5 text-xs text-ink font-semibold">
                <Building2 size={15} className="text-forest shrink-0" />
                SOP Operational Authority Reminder
              </AlertTitle>
              <AlertDescription className="text-muted leading-relaxed text-xs">
                BHUSHAKTI AI serves purely as an intelligent decision-support platform. Warning broadcasts,
                road closures, and evacuation directives must be formally sanctioned by the Competent District Authority (DDMA / SDMA).
              </AlertDescription>
            </div>
          </Alert>
        </div>
      </div>
    </div>
  );
}
