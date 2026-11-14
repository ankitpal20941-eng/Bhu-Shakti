import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Filter, Layers, ListFilter, Map as MapIcon, Search } from "lucide-react";
import clsx from "clsx";
import { api, qs } from "../lib/api";
import { fmtNumber, riskMeta, timeAgo } from "../lib/format";
import type { Alert, ZoneCollection } from "../lib/types";
import { useUi } from "../store/ui";
import { useSession } from "../store/session";
import { MapView } from "../components/MapView";
import { ZoneDrawer } from "../components/ZoneDrawer";
import { Card, CardHeader, EmptyState, ErrorState, Loading, PriorityBadge, RiskBadge, StateBadge, UncalibratedNote } from "../components/ui";
import { useFallbackPolling } from "../hooks/useLiveUpdates";

const LAYER_LABELS: Array<{ key: keyof ReturnType<typeof useUi.getState>["layers"]; label: string }> = [
  { key: "risk", label: "Risk units" },
  { key: "roads", label: "Roads" },
  { key: "assets", label: "Exposure assets" },
  { key: "incidents", label: "Historical" },
  { key: "reports", label: "Field reports" },
];

type Feature = GeoJSON.Feature<GeoJSON.Geometry, Record<string, unknown>>;

export default function RiskMap() {
  const ui = useUi();
  const selectedZoneId = ui.selectedZoneId;
  const has = useSession((s) => s.has);
  const polling = useFallbackPolling(true);

  const districts = useQuery({
    queryKey: ["public-config"],
    queryFn: () => api<{ districts: Array<{ code: string; name: string; state: string }> }>("/api/v1/public/config"),
    staleTime: 300_000,
  });

  const zonesQuery = useQuery({
    queryKey: ["risk-zones", ui.districtFilter, ui.riskFilter, ui.priorityFilter],
    queryFn: () => api<ZoneCollection>(`/api/v1/risk-zones${qs({
      limit: 2000,
      district_code: ui.districtFilter || undefined,
      risk_level: ui.riskFilter || undefined,
      priority_level: ui.priorityFilter || undefined,
    })}`),
    ...polling,
  });

  const roadsQuery = useQuery({
    queryKey: ["roads", ui.districtFilter],
    queryFn: () => api<{ roads: Array<{ id: number; name: string; ref: string; geometry: GeoJSON.LineString; segments: Array<{ id: number; status: string; name: string; length_km: number; status_source: string }> }> }>(
      `/api/v1/roads${qs({ district_code: ui.districtFilter || undefined })}`,
    ),
    enabled: ui.layers.roads,
    ...polling,
  });
  const infraQuery = useQuery({
    queryKey: ["infrastructure", ui.districtFilter],
    queryFn: () => api<{ assets: Array<{ id: number; kind: string; name: string; lat: number; lon: number }> }>(
      `/api/v1/infrastructure${qs({ district_code: ui.districtFilter || undefined, limit: 1000 })}`,
    ),
    enabled: ui.layers.assets,
    ...polling,
  });
  const incidentsQuery = useQuery({
    queryKey: ["incidents", ui.districtFilter],
    queryFn: () => api<{ incidents: Array<{ id: number; lat: number; lon: number; occurred_on: string; verified: boolean }> }>(
      `/api/v1/incidents${qs({ district_code: ui.districtFilter || undefined, limit: 500 })}`,
    ),
    enabled: ui.layers.incidents,
    ...polling,
  });
  const reportsQuery = useQuery({
    queryKey: ["reports", "map", ui.districtFilter],
    queryFn: () => api<{ reports: Array<{ id: number; lat: number | null; lon: number | null; status: string; hazard_type: string }> }>(
      `/api/v1/reports${qs({ district_code: ui.districtFilter || undefined, limit: 200 })}`,
    ),
    enabled: ui.layers.reports && has("reports:read"),
    ...polling,
  });
  const alertsQuery = useQuery({
    queryKey: ["alerts", "map"],
    queryFn: () => api<{ alerts: Alert[] }>("/api/v1/alerts?limit=50"),
    enabled: has("alerts:read"),
    ...polling,
  });

  const features = useMemo(() => {
    const all = zonesQuery.data?.features ?? [];
    if (!ui.search.trim()) return all;
    const needle = ui.search.toLowerCase();
    return all.filter((zone) =>
      zone.properties.name.toLowerCase().includes(needle)
      || zone.properties.code.toLowerCase().includes(needle)
      || zone.properties.district_name.toLowerCase().includes(needle));
  }, [zonesQuery.data, ui.search]);

  const roads = useMemo<Feature[]>(() => {
    const features: Feature[] = [];
    for (const road of roadsQuery.data?.roads ?? []) {
      for (const segment of road.segments) {
        features.push({
          type: "Feature",
          geometry: road.geometry,
          properties: {
            id: segment.id, name: `${road.ref} · ${segment.name}`,
            status: segment.status,
            color: segment.status === "BLOCKED" ? "#b91c1c"
              : segment.status === "AT_RISK" ? "#c2410c"
                : segment.status === "RESTRICTED" ? "#a16207" : "#59635c",
          },
        });
      }
    }
    return features;
  }, [roadsQuery.data]);

  const assets = useMemo<Feature[]>(() => (infraQuery.data?.assets ?? [])
    .filter((asset) => asset.lat && asset.lon)
    .map((asset) => ({
      type: "Feature" as const,
      geometry: { type: "Point" as const, coordinates: [asset.lon, asset.lat] },
      properties: {
        id: asset.id, kind: asset.kind, name: asset.name,
        color: asset.kind === "hospital" ? "#2f5d7c" : asset.kind === "bridge" ? "#6b4f3a" : "#5b6660",
      },
    })), [infraQuery.data]);

  const incidents = useMemo<Feature[]>(() => (incidentsQuery.data?.incidents ?? []).map((incident) => ({
    type: "Feature" as const,
    geometry: { type: "Point" as const, coordinates: [incident.lon, incident.lat] },
    properties: { id: incident.id },
  })), [incidentsQuery.data]);

  const reports = useMemo<Feature[]>(() => (reportsQuery.data?.reports ?? [])
    .filter((report) => report.lat !== null && report.lon !== null)
    .map((report) => ({
      type: "Feature" as const,
      geometry: { type: "Point" as const, coordinates: [report.lon as number, report.lat as number] },
      properties: {
        id: report.id,
        color: report.status === "VERIFIED" ? "#2f7d4f" : report.status === "REJECTED" ? "#6b7280" : "#a16207",
      },
    })), [reportsQuery.data]);

  const activeAlerts = useMemo(
    () => (alertsQuery.data?.alerts ?? []).filter((alert) => ["APPROVED", "DELIVERED"].includes(alert.status)),
    [alertsQuery.data],
  );

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Live Risk Map</h1>
          <p className="text-sm text-muted">
            {fmtNumber(features.length)} units · computed {timeAgo(zonesQuery.data?.meta.generated_at)} ·
            {" "}{activeAlerts.length} approved advisories displayed as outlines only
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          <button className={clsx("btn btn-sm", !ui.layers.susceptibility && "border-forest text-forest")} onClick={() => ui.toggleLayer("susceptibility")}>
            <Layers size={14} /> {ui.layers.susceptibility ? "Terrain propensity" : "Operational hazard"}
          </button>
        </div>
      </div>

      <Card className="p-2">
        <div className="flex flex-wrap items-center gap-1.5">
          <div className="relative min-w-[180px] flex-1">
            <Search size={14} className="pointer-events-none absolute left-2 top-1/2 -translate-y-1/2 text-muted" />
            <input className="input pl-7" placeholder="Search unit, code or district" value={ui.search} onChange={(event) => ui.setSearch(event.target.value)} aria-label="Search risk units" />
          </div>
          <select className="select w-auto" value={ui.districtFilter} onChange={(event) => ui.setDistrictFilter(event.target.value)} aria-label="Filter by district">
            <option value="">All districts</option>
            {(districts.data?.districts ?? []).map((district) => (
              <option key={district.code} value={district.code}>{district.name}</option>
            ))}
          </select>
          <select className="select w-auto" value={ui.riskFilter} onChange={(event) => ui.setRiskFilter(event.target.value)} aria-label="Filter by hazard level">
            <option value="">Any hazard</option>
            {(["SAFE", "WATCH", "WARNING", "CRITICAL"] as const).map((level) => (
              <option key={level} value={level}>{riskMeta[level].label}</option>
            ))}
          </select>
          <select className="select w-auto" value={ui.priorityFilter} onChange={(event) => ui.setPriorityFilter(event.target.value)} aria-label="Filter by priority">
            <option value="">Any priority</option>
            {["P1", "P2", "P3", "P4"].map((priority) => <option key={priority} value={priority}>{priority}</option>)}
          </select>
          <div className="flex flex-wrap items-center gap-1">
            {LAYER_LABELS.map((layer) => (
              <button
                key={layer.key}
                className={clsx("btn btn-sm", ui.layers[layer.key] ? "border-forest text-forest" : "text-muted")}
                onClick={() => ui.toggleLayer(layer.key)}
                aria-pressed={ui.layers[layer.key]}
              >
                {layer.label}
              </button>
            ))}
          </div>
        </div>
      </Card>

      <div className="grid gap-3 lg:grid-cols-[300px_minmax(0,1fr)]">
        <Card className="hidden max-h-[calc(100vh-260px)] overflow-hidden lg:flex lg:flex-col">
          <CardHeader title="Ranked units" subtitle="Hazard first; priority is separate" icon={<ListFilter size={16} />} />
          <div className="flex-1 overflow-y-auto">
            {zonesQuery.isLoading ? <Loading label="Loading units" /> : null}
            {zonesQuery.error ? <div className="p-3"><ErrorState error={zonesQuery.error} onRetry={() => zonesQuery.refetch()} /></div> : null}
            {features.map((zone) => (
              <button
                key={zone.properties.id}
                className={clsx("flex w-full flex-col gap-1 border-b border-line px-3 py-2 text-left hover:bg-surface-2", selectedZoneId === zone.properties.id && "bg-forest-soft")}
                onClick={() => ui.selectZone(zone.properties.id)}
              >
                <span className="flex items-center justify-between gap-2">
                  <span className="truncate text-xs font-medium">{zone.properties.name}</span>
                  <span className="numeric text-xs">{fmtNumber(zone.properties.hazard_index, 0)}</span>
                </span>
                <span className="flex flex-wrap items-center gap-1">
                  <RiskBadge level={zone.properties.hazard_level} />
                  <PriorityBadge level={zone.properties.priority_level} />
                  {zone.properties.weather_source_state && zone.properties.weather_source_state !== "LIVE" ? (
                    <StateBadge state={zone.properties.weather_source_state} />
                  ) : null}
                </span>
              </button>
            ))}
            {!features.length && !zonesQuery.isLoading ? <EmptyState title="No units match these filters" body="Adjust the district, hazard or priority filter." /> : null}
          </div>
        </Card>

        <Card className="relative overflow-hidden">
          <div className="h-[calc(100vh-260px)] min-h-[420px]">
            <MapView
              zones={features}
              colorMode={ui.layers.susceptibility ? "susceptibility" : "hazard"}
              layers={ui.layers}
              selectedId={selectedZoneId}
              onSelect={ui.selectZone}
              roads={{ type: "FeatureCollection", features: roads }}
              assets={{ type: "FeatureCollection", features: assets }}
              incidents={{ type: "FeatureCollection", features: incidents }}
              reports={{ type: "FeatureCollection", features: reports }}
              lowBandwidth={ui.lowBandwidth}
            />
          </div>
          <div className="pointer-events-none absolute left-3 top-3 z-10 max-w-[320px] rounded-lg border border-line bg-surface/95 px-2.5 py-1.5 text-2xs shadow-card">
            <div className="flex items-center gap-1.5 font-semibold"><MapIcon size={12} /> Operational hazard index</div>
            <div className="text-muted">Not a probability. {ui.layers.susceptibility ? "Showing terrain propensity layer." : "Dry weather keeps hazard near the susceptibility floor."}</div>
          </div>
          <div className="absolute right-3 top-3 z-10">
            <UncalibratedNote compact />
          </div>
        </Card>
      </div>

      <div className="flex flex-wrap items-center gap-2 text-2xs text-muted">
        <Filter size={12} /> Basemap © OpenStreetMap contributors. Zone geometry is a generated grid; district envelopes and road corridors are approximate pilot placeholders.
      </div>

      <ZoneDrawer zoneId={selectedZoneId} onClose={() => ui.selectZone(null)} />
    </div>
  );
}
