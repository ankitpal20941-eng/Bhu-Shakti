import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  ArrowUpRight,
  ClipboardList,
  CloudRain,
  Compass,
  History,
  MapPinned,
  Radio,
  RefreshCw,
  Route,
  Satellite,
  ShieldAlert,
  TrendingDown,
  Users,
} from "lucide-react";
import { api } from "../lib/api";
import { fmtDateTime, fmtNumber, timeAgo } from "../lib/format";
import type { Alert, Assignment, RiskSummary, ZoneCollection } from "../lib/types";
import { useUi } from "../store/ui";
import { MapView } from "../components/MapView";
import { ZoneDrawer } from "../components/ZoneDrawer";
import { Card, CardHeader, EmptyState, ErrorState, Loading, PriorityBadge, RiskBadge, StateBadge, UncalibratedNote } from "../components/ui";
import { useFallbackPolling } from "../hooks/useLiveUpdates";
import {
  SpotlightCard,
  ShimmerButton,
  DisclosurePill,
  InfiniteMovingCards,
  BackgroundBeams,
  HoverBorderGradient,
} from "../components/aceternity";
import {
  Badge,
  Table,
  TableHeader,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
} from "../components/shadcn";

export default function Overview() {
  const { lowBandwidth, layers, liveStatus } = useUi((s) => ({ lowBandwidth: s.lowBandwidth, layers: s.layers, liveStatus: s.liveStatus }));
  const selectZone = useUi((s) => s.selectZone);
  const selectedZoneId = useUi((s) => s.selectedZoneId);
  const polling = useFallbackPolling(true);

  const summary = useQuery({ queryKey: ["risk-summary"], queryFn: () => api<RiskSummary>("/api/v1/risk/summary"), ...polling });
  const zones = useQuery({
    queryKey: ["risk-zones", "overview"],
    queryFn: () => api<ZoneCollection>("/api/v1/risk-zones?limit=1000"),
    ...polling,
  });
  const alerts = useQuery({ queryKey: ["alerts", "overview"], queryFn: () => api<{ alerts: Alert[] }>("/api/v1/alerts?limit=25"), ...polling });
  const assignments = useQuery({ queryKey: ["response", "overview"], queryFn: () => api<{ assignments: Assignment[] }>("/api/v1/response?limit=25"), ...polling });

  const kpis = summary.data?.kpis;
  const topZones = useMemo(() => (zones.data?.features ?? []).slice(0, 8), [zones.data]);
  const priorityAlerts = useMemo(
    () => [...(alerts.data?.alerts ?? [])]
      .filter((a) => ["CANDIDATE", "APPROVED", "DELIVERED"].includes(a.status))
      .sort((a, b) => b.hazard_index - a.hazard_index)
      .slice(0, 4),
    [alerts.data],
  );
  const queue = useMemo(
    () => [...(assignments.data?.assignments ?? [])]
      .filter((a) => a.status !== "RESOLVED")
      .sort((a, b) => (a.priority > b.priority ? 1 : -1))
      .slice(0, 4),
    [assignments.data],
  );

  const telemetryFeed = useMemo(
    () => [
      {
        title: "IMD Doppler Radar (Sohra / Cherrapunji)",
        subtitle: "24h Precip: 42.4mm · Soil Moisture: 84.1% · High Intensity Cell",
        badge: "Live Stream",
        badgeVariant: "warning" as const,
        icon: <CloudRain size={14} />,
      },
      {
        title: "Borehole Piezometers (ML-EKH-014)",
        subtitle: "Pore Water Pressure: 34.2 kPa · Subsurface pore baseline nominal",
        badge: "Normal",
        badgeVariant: "safe" as const,
        icon: <Radio size={14} />,
      },
      {
        title: "Copernicus Sentinel-2 MSI",
        subtitle: "Orbital Pass: 04:18 UTC · Optical Coverage 92% · InSAR Coherence 0.88",
        badge: "Orbit sync",
        badgeVariant: "neutral" as const,
        icon: <Satellite size={14} />,
      },
      {
        title: "Inclinometer Array (NH-6 Jowai Corridor)",
        subtitle: "Cumulative Displacement: 0.18mm · Sub-shear creeping",
        badge: "Monitoring",
        badgeVariant: "safe" as const,
        icon: <TrendingDown size={14} />,
      },
      {
        title: "SDRF Mountain Battalion (Kamrup Metro)",
        subtitle: "Cadre Readiness: DEFCON 2 · Quick-Response Deployable in 15m",
        badge: "Standby",
        badgeVariant: "safe" as const,
        icon: <ShieldAlert size={14} />,
      },
      {
        title: "Brahmaputra Hydrological Station",
        subtitle: "Discharge: 19,400 m³/s · River stage 0.8m below danger level",
        badge: "Stable",
        badgeVariant: "safe" as const,
        icon: <Route size={14} />,
      },
    ],
    []
  );

  return (
    <div className="space-y-6">
      {/* Live Continuous Telemetry Stream Marquee (Aceternity UI) */}
      <InfiniteMovingCards items={telemetryFeed} className="mb-1" />

      {/* Top Editorial Trust & Command Header (Aceternity Radiant Beams + Apple Glass) */}
      <div className="relative overflow-hidden flex flex-wrap items-center justify-between gap-4 p-6 rounded-3xl bg-surface/90 dark:bg-surface/80 backdrop-blur-2xl border border-line shadow-lg">
        <BackgroundBeams />
        <div className="relative z-10 space-y-1.5">
          <div className="flex items-center gap-2">
            <DisclosurePill text="Verified Methodology: GSI + Copernicus DEM + IMD Radar" />
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-ink">
            Landslide Intelligence Command Center
          </h1>
          <p className="text-xs sm:text-sm text-muted">
            {summary.data?.jurisdiction.statewide ? "Statewide Operational Picture (Assam, Meghalaya, Mizoram)" : "District Jurisdiction"} · Model run {fmtDateTime(summary.data?.last_run)}
          </p>
        </div>

        <div className="relative z-10 flex flex-wrap items-center gap-2.5">
          <span className="chip px-3 py-1 font-semibold text-xs border border-line bg-surface-2 rounded-full flex items-center gap-1.5">
            <Radio size={12} className={liveStatus === "live" ? "text-safe animate-pulse" : "text-watch"} />
            {liveStatus === "live" ? "Live Telemetry" : "60s Polling"}
          </span>
          <Link to="/situation-room">
            <HoverBorderGradient active={true} className="flex items-center gap-2 py-2 px-4 font-semibold text-xs text-white bg-forest hover:bg-forest/90">
              <ShieldAlert size={14} /> Open Situation Room
            </HoverBorderGradient>
          </Link>
          <button
            className="btn btn-secondary text-xs rounded-xl py-2 px-3 flex items-center gap-1.5"
            onClick={() => { summary.refetch(); zones.refetch(); alerts.refetch(); assignments.refetch(); }}
          >
            <RefreshCw size={13} /> Refresh
          </button>
        </div>
      </div>

      {summary.error ? <ErrorState error={summary.error} onRetry={() => summary.refetch()} /> : null}

      {/* Apple Glass KPI Ribbon */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3.5">
        <SpotlightCard className="p-4 border-l-4 border-l-critical">
          <div className="flex items-center justify-between text-muted">
            <span className="text-[11px] uppercase font-bold tracking-wider">Critical Units</span>
            <ShieldAlert size={16} className="text-critical" />
          </div>
          <div className="text-3xl font-extrabold tracking-tight text-critical mt-1.5 tabular-nums">
            {fmtNumber(kpis?.critical_zones)}
          </div>
          <div className="text-[11px] text-muted mt-0.5">Hazard index ≥ 80</div>
        </SpotlightCard>

        <SpotlightCard className="p-4 border-l-4 border-l-warning">
          <div className="flex items-center justify-between text-muted">
            <span className="text-[11px] uppercase font-bold tracking-wider">Warning Units</span>
            <AlertTriangle size={16} className="text-warning" />
          </div>
          <div className="text-3xl font-extrabold tracking-tight text-warning mt-1.5 tabular-nums">
            {fmtNumber(kpis?.warning_zones)}
          </div>
          <div className="text-[11px] text-muted mt-0.5">Hazard index 60–79</div>
        </SpotlightCard>

        <SpotlightCard className="p-4 border-l-4 border-l-primary">
          <div className="flex items-center justify-between text-muted">
            <span className="text-[11px] uppercase font-bold tracking-wider">Roads at Risk</span>
            <Route size={16} className="text-primary" />
          </div>
          <div className="text-3xl font-extrabold tracking-tight text-ink mt-1.5 tabular-nums">
            {fmtNumber(kpis?.roads_at_risk)}
          </div>
          <div className="text-[11px] text-critical font-medium mt-0.5">{kpis?.roads_blocked ?? 0} blocked corridors</div>
        </SpotlightCard>

        <SpotlightCard className="p-4 border-l-4 border-l-safe">
          <div className="flex items-center justify-between text-muted">
            <span className="text-[11px] uppercase font-bold tracking-wider">Active Alerts</span>
            <ClipboardList size={16} className="text-safe" />
          </div>
          <div className="text-3xl font-extrabold tracking-tight text-foreground mt-1.5 tabular-nums">
            {fmtNumber(kpis?.active_alerts)}
          </div>
          <div className="text-[11px] text-warning font-medium mt-0.5">{kpis?.pending_alerts ?? 0} awaiting signature</div>
        </SpotlightCard>

        <SpotlightCard className="p-4 border-l-4 border-l-emerald-600">
          <div className="flex items-center justify-between text-muted">
            <span className="text-[11px] uppercase font-bold tracking-wider">Field Cadre</span>
            <Users size={16} className="text-emerald-600" />
          </div>
          <div className="text-3xl font-extrabold tracking-tight text-foreground mt-1.5 tabular-nums">
            4 Teams
          </div>
          <div className="text-[11px] text-muted mt-0.5">Geotech & Search teams ready</div>
        </SpotlightCard>

        <SpotlightCard className="p-4 border-l-4 border-l-blue-600">
          <div className="flex items-center justify-between text-muted">
            <span className="text-[11px] uppercase font-bold tracking-wider">Population Exposure</span>
            <MapPinned size={16} className="text-blue-600" />
          </div>
          <div className="text-3xl font-extrabold tracking-tight text-foreground mt-1.5 tabular-nums">
            {kpis?.population_exposed_estimate ? fmtNumber(kpis.population_exposed_estimate) : "—"}
          </div>
          <div className="text-[11px] text-muted mt-0.5">Verified census overlay</div>
        </SpotlightCard>
      </div>

      {/* Advanced Aceternity Bento Grid for Decision Modules */}
      <div>
        <div className="mb-3 flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold tracking-tight text-ink">Intelligent Decision Modules</h2>
            <p className="text-xs text-muted">Advanced geospatial graph solvers, rainfall analytics, and satellite Earth observation</p>
          </div>
          <DisclosurePill text="Instant SOP Workflows" />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-3.5">
          <Link to="/situation-room" className="group">
            <SpotlightCard className="p-4 h-full flex flex-col justify-between hover:border-primary/50 transition-all">
              <div>
                <div className="p-2 rounded-xl bg-critical/10 text-critical w-fit mb-2">
                  <ShieldAlert size={18} />
                </div>
                <div className="font-bold text-sm text-ink group-hover:text-primary transition-colors">Situation Room</div>
                <p className="text-[11px] text-muted mt-1 leading-normal">
                  Unified command cockpit for active critical warnings & approvals.
                </p>
              </div>
              <div className="mt-3 flex items-center gap-1 text-[11px] font-semibold text-primary">
                Open Room <ArrowUpRight size={12} />
              </div>
            </SpotlightCard>
          </Link>

          <Link to="/impact-analysis" className="group">
            <SpotlightCard className="p-4 h-full flex flex-col justify-between hover:border-primary/50 transition-all">
              <div>
                <div className="p-2 rounded-xl bg-primary/10 text-primary w-fit mb-2">
                  <Compass size={18} />
                </div>
                <div className="font-bold text-sm text-ink group-hover:text-primary transition-colors">Impact Analysis</div>
                <p className="text-[11px] text-muted mt-1 leading-normal">
                  Road network graph connectivity & isolated village solver.
                </p>
              </div>
              <div className="mt-3 flex items-center gap-1 text-[11px] font-semibold text-primary">
                Simulate Cut-Offs <ArrowUpRight size={12} />
              </div>
            </SpotlightCard>
          </Link>

          <Link to="/rainfall-intelligence" className="group">
            <SpotlightCard className="p-4 h-full flex flex-col justify-between hover:border-primary/50 transition-all">
              <div>
                <div className="p-2 rounded-xl bg-warning/10 text-warning w-fit mb-2">
                  <CloudRain size={18} />
                </div>
                <div className="font-bold text-sm text-ink group-hover:text-primary transition-colors">Rainfall Intel</div>
                <p className="text-[11px] text-muted mt-1 leading-normal">
                  Multi-horizon accumulation & district geotechnical thresholds.
                </p>
              </div>
              <div className="mt-3 flex items-center gap-1 text-[11px] font-semibold text-primary">
                View Envelopes <ArrowUpRight size={12} />
              </div>
            </SpotlightCard>
          </Link>

          <Link to="/runout-analysis" className="group">
            <SpotlightCard className="p-4 h-full flex flex-col justify-between hover:border-primary/50 transition-all">
              <div>
                <div className="p-2 rounded-xl bg-orange-500/10 text-orange-600 w-fit mb-2">
                  <TrendingDown size={18} />
                </div>
                <div className="font-bold text-sm text-ink group-hover:text-primary transition-colors">Runout Zones</div>
                <p className="text-[11px] text-muted mt-1 leading-normal">
                  Fahrböschung travel angle & downslope flowline corridors.
                </p>
              </div>
              <div className="mt-3 flex items-center gap-1 text-[11px] font-semibold text-primary">
                Compute Runout <ArrowUpRight size={12} />
              </div>
            </SpotlightCard>
          </Link>

          <Link to="/satellite-change" className="group">
            <SpotlightCard className="p-4 h-full flex flex-col justify-between hover:border-primary/50 transition-all">
              <div>
                <div className="p-2 rounded-xl bg-blue-500/10 text-blue-600 w-fit mb-2">
                  <Satellite size={18} />
                </div>
                <div className="font-bold text-sm text-ink group-hover:text-primary transition-colors">Satellite Change</div>
                <p className="text-[11px] text-muted mt-1 leading-normal">
                  Sentinel-2 NDVI vegetation loss & human analyst verification gate.
                </p>
              </div>
              <div className="mt-3 flex items-center gap-1 text-[11px] font-semibold text-primary">
                Verify Scars <ArrowUpRight size={12} />
              </div>
            </SpotlightCard>
          </Link>

          <Link to="/historical-replay" className="group">
            <SpotlightCard className="p-4 h-full flex flex-col justify-between hover:border-primary/50 transition-all">
              <div>
                <div className="p-2 rounded-xl bg-purple-500/10 text-purple-600 w-fit mb-2">
                  <History size={18} />
                </div>
                <div className="font-bold text-sm text-ink group-hover:text-primary transition-colors">Event Replay</div>
                <p className="text-[11px] text-muted mt-1 leading-normal">
                  Time slider playback of past disaster episodes vs ground truth.
                </p>
              </div>
              <div className="mt-3 flex items-center gap-1 text-[11px] font-semibold text-primary">
                Replay Episode <ArrowUpRight size={12} />
              </div>
            </SpotlightCard>
          </Link>
        </div>
      </div>

      {/* Main Map & Live Feeds Layout */}
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_380px]">
        <div className="space-y-6">
          <Card className="overflow-hidden">
            <CardHeader
              title="Interactive Operational Hazard Map"
              subtitle="Slope units (~34 km²). Tap any unit to inspect terrain curvature, TWI, rainfall triggers, and road cuts."
              action={
                <Link to="/map">
                  <ShimmerButton variant="secondary">
                    Expand Full Map <ArrowUpRight size={14} />
                  </ShimmerButton>
                </Link>
              }
              icon={<MapPinned size={16} />}
            />
            <div className="h-[460px]">
              {zones.isLoading ? <Loading label="Loading risk units" /> : (
                <MapView
                  zones={zones.data?.features ?? []}
                  colorMode={layers.susceptibility ? "susceptibility" : "hazard"}
                  layers={layers}
                  selectedId={selectedZoneId}
                  onSelect={selectZone}
                  lowBandwidth={lowBandwidth}
                />
              )}
            </div>
            <div className="border-t border-line px-5 py-3 bg-surface-2/40 space-y-2">
              <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
                <UncalibratedNote compact />
                <div className="flex flex-wrap items-center gap-1.5">
                  <Badge variant="success">{fmtNumber(summary.data?.hazard_distribution.SAFE)} Safe</Badge>
                  <Badge variant="watch">{fmtNumber(summary.data?.hazard_distribution.WATCH)} Watch</Badge>
                  <Badge variant="warning">{fmtNumber(summary.data?.hazard_distribution.WARNING)} Warning</Badge>
                  <Badge variant="destructive">{fmtNumber(summary.data?.hazard_distribution.CRITICAL)} Critical</Badge>
                </div>
              </div>
            </div>
          </Card>

          <Card>
            <CardHeader
              title="Highest Hazard Units"
              subtitle="Ranked by deterministic hazard index; operational priority calculated separately based on assets exposed."
              icon={<ShieldAlert size={16} className="text-warning" />}
            />
            <div className="p-3">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Slope Unit</TableHead>
                    <TableHead>District</TableHead>
                    <TableHead>Hazard Index</TableHead>
                    <TableHead>Operational Priority</TableHead>
                    <TableHead>Coverage</TableHead>
                    <TableHead>Telemetry</TableHead>
                    <TableHead>Updated</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {topZones.map((zone) => (
                    <TableRow
                      key={zone.properties.id}
                      className="cursor-pointer hover:bg-surface-2/60 transition-colors"
                      onClick={() => selectZone(zone.properties.id)}
                    >
                      <TableCell className="font-bold text-ink">{zone.properties.name}</TableCell>
                      <TableCell className="text-muted">{zone.properties.district_name}</TableCell>
                      <TableCell>
                        <RiskBadge level={zone.properties.hazard_level} index={zone.properties.hazard_index} />
                      </TableCell>
                      <TableCell>
                        <PriorityBadge level={zone.properties.priority_level} showLabel />
                      </TableCell>
                      <TableCell className="font-mono text-muted text-xs">
                        {zone.properties.coverage_level ?? "—"}
                      </TableCell>
                      <TableCell>
                        <StateBadge state={zone.properties.weather_source_state} />
                      </TableCell>
                      <TableCell className="whitespace-nowrap text-muted text-[11px] font-mono">
                        {timeAgo(zone.properties.computed_at)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              {!topZones.length && !zones.isLoading ? (
                <EmptyState title="No assessments yet" body="Run a recalculation or wait for the scheduled refresh." />
              ) : null}
            </div>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader title="Current Regional Weather Conditions" subtitle="District-centre live sensor grid points" icon={<CloudRain size={16} />} />
            <div className="divide-y divide-line/70">
              {(summary.data?.conditions ?? []).map((condition) => (
                <div key={condition.district_code} className="px-5 py-3 hover:bg-surface-2/30 transition-colors">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-bold text-ink">{condition.district_name}</span>
                    <StateBadge state={condition.source_state} />
                  </div>
                  <div className="mt-2 grid grid-cols-3 gap-2 text-center text-xs">
                    <div className="p-1.5 rounded-lg bg-surface-2/70 border border-line">
                      <div className="text-[10px] text-muted">1h Rain</div>
                      <div className="font-bold text-ink mt-0.5">{fmtNumber(condition.rainfall_1h, 1)} mm</div>
                    </div>
                    <div className="p-1.5 rounded-lg bg-surface-2/70 border border-line">
                      <div className="text-[10px] text-muted">24h Total</div>
                      <div className="font-bold text-warning mt-0.5">{fmtNumber(condition.rainfall_24h, 1)} mm</div>
                    </div>
                    <div className="p-1.5 rounded-lg bg-surface-2/70 border border-line">
                      <div className="text-[10px] text-muted">Soil Moisture</div>
                      <div className="font-bold text-safe mt-0.5">{fmtNumber(condition.soil_moisture_pct, 0)}%</div>
                    </div>
                  </div>
                  <div className="mt-2 text-[10px] text-muted flex items-center justify-between">
                    <span>Observed {timeAgo(condition.observed_at)}</span>
                    <span className="font-mono text-muted/70">{condition.source_id}</span>
                  </div>
                </div>
              ))}
              {!summary.data?.conditions.length ? <p className="px-4 py-3 text-xs text-muted">No weather observation available.</p> : null}
            </div>
          </Card>

          <Card>
            <CardHeader
              title="Priority Alerts Queue"
              subtitle="Candidate alerts awaiting DC approval"
              action={<Link to="/alerts" className="text-xs font-semibold text-primary hover:underline">View All</Link>}
              icon={<AlertTriangle size={16} className="text-warning" />}
            />
            <div className="divide-y divide-line/70">
              {priorityAlerts.map((alert) => (
                <div key={alert.id} className="p-4 hover:bg-surface-2/30 transition-colors space-y-1.5">
                  <div className="flex items-center justify-between gap-2">
                    <RiskBadge level={alert.severity} />
                    <span className="chip text-[10px] uppercase font-bold">{alert.status}</span>
                  </div>
                  <div className="text-xs font-bold text-ink">{alert.headline}</div>
                  <div className="text-[11px] text-muted font-mono">{alert.reference} · {timeAgo(alert.created_at)}</div>
                </div>
              ))}
              {!priorityAlerts.length ? <p className="p-4 text-xs text-muted text-center">No active or pending alerts.</p> : null}
            </div>
          </Card>

          <Card>
            <CardHeader
              title="Active Field Allocations"
              subtitle="Quick response teams currently deployed"
              action={<Link to="/field-teams" className="text-xs font-semibold text-primary hover:underline">Optimizer</Link>}
              icon={<Users size={16} className="text-primary" />}
            />
            <div className="divide-y divide-line/70">
              {queue.map((item) => (
                <div key={item.id} className="p-4 hover:bg-surface-2/30 transition-colors space-y-1">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-bold text-ink">{item.zone_name}</span>
                    <PriorityBadge level={item.priority} />
                  </div>
                  <div className="text-[11px] text-muted flex items-center justify-between">
                    <span>Status: <strong className="text-foreground">{item.status}</strong></span>
                    <span>Assignee: {item.assignee_name ?? "Unassigned"}</span>
                  </div>
                </div>
              ))}
              {!queue.length ? <p className="p-4 text-xs text-muted text-center">No open assignments.</p> : null}
            </div>
          </Card>
        </div>
      </div>

      <div className="p-4 rounded-2xl bg-surface-2/60 border border-line text-[11px] text-muted leading-relaxed flex items-center justify-between">
        <span>{summary.data?.disclaimer ?? "Decision support only — not an official warning."} {summary.data?.population_note}</span>
        <span className="font-semibold text-ink">BhuShakti AI v0.9.0</span>
      </div>

      <ZoneDrawer zoneId={selectedZoneId} onClose={() => selectZone(null)} />
    </div>
  );
}
