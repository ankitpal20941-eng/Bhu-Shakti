import { useEffect, useRef } from "react";
import maplibregl, { type Map as MlMap } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { ZoneFeature } from "../lib/types";
import type { LayerKey } from "../store/ui";
import { riskMeta } from "../lib/format";

const OSM_ATTRIBUTION = '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

type FeatureCollection = GeoJSON.FeatureCollection<GeoJSON.Geometry, Record<string, unknown>>;

interface MapViewProps {
  zones: ZoneFeature[];
  colorMode: "hazard" | "susceptibility";
  layers: Record<LayerKey, boolean>;
  selectedId: number | null;
  onSelect: (id: number) => void;
  roads?: FeatureCollection | null;
  assets?: FeatureCollection | null;
  incidents?: FeatureCollection | null;
  reports?: FeatureCollection | null;
  lowBandwidth: boolean;
  className?: string;
}

function zoneColor(zone: ZoneFeature, mode: "hazard" | "susceptibility"): string {
  if (mode === "susceptibility") {
    const value = zone.properties.susceptibility_index ?? 0;
    if (value >= 75) return "rgba(120,53,15,0.55)";
    if (value >= 55) return "rgba(161,98,7,0.47)";
    if (value >= 35) return "rgba(202,138,4,0.35)";
    return "rgba(74,124,89,0.25)";
  }
  const level = zone.properties.hazard_level;
  return level ? riskMeta[level].fill : "rgba(120,130,125,0.2)";
}

export function MapView({
  zones, colorMode, layers, selectedId, onSelect, roads, assets, incidents, reports, lowBandwidth, className,
}: MapViewProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MlMap | null>(null);
  const readyRef = useRef(false);
  const fittedRef = useRef(false);
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: {
        version: 8,
        sources: lowBandwidth
          ? {}
          : {
              osm: {
                type: "raster",
                tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
                tileSize: 256,
                attribution: OSM_ATTRIBUTION,
                maxzoom: 18,
              },
            },
        layers: lowBandwidth
          ? [{ id: "bg", type: "background", paint: { "background-color": "#e8ebe4" } }]
          : [{ id: "osm", type: "raster", source: "osm" }],
      },
      center: [91.9, 25.6],
      zoom: 7.4,
      attributionControl: false,
      maxZoom: 16,
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    map.addControl(new maplibregl.ScaleControl({ unit: "metric" }), "bottom-left");
    map.addControl(new maplibregl.AttributionControl({ compact: true }), "bottom-right");
    mapRef.current = map;

    map.on("load", () => {
      readyRef.current = true;
      map.addSource("zones", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      map.addSource("roads", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      map.addSource("assets", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      map.addSource("incidents", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      map.addSource("reports", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      map.addSource("selected", { type: "geojson", data: { type: "FeatureCollection", features: [] } });

      map.addLayer({
        id: "zone-fill", type: "fill", source: "zones",
        paint: { "fill-color": ["get", "color"], "fill-opacity": 0.85 },
      });
      map.addLayer({
        id: "zone-outline", type: "line", source: "zones",
        paint: { "line-color": "rgba(22,32,27,0.25)", "line-width": 0.6 },
      });
      map.addLayer({
        id: "roads-line", type: "line", source: "roads",
        paint: {
          "line-color": ["get", "color"],
          "line-width": ["case", ["==", ["get", "status"], "BLOCKED"], 3.2, 2.2],
          "line-opacity": 0.9,
        },
      });
      map.addLayer({
        id: "assets-circle", type: "circle", source: "assets",
        paint: {
          "circle-radius": ["case", ["==", ["get", "kind"], "settlements"], 4.5, 3.5],
          "circle-color": ["get", "color"],
          "circle-stroke-color": "#ffffff", "circle-stroke-width": 0.8,
        },
      });
      map.addLayer({
        id: "incidents-circle", type: "circle", source: "incidents",
        paint: {
          "circle-radius": 3.2, "circle-color": "#4b5563",
          "circle-stroke-color": "#ffffff", "circle-stroke-width": 0.7,
        },
      });
      map.addLayer({
        id: "reports-circle", type: "circle", source: "reports",
        paint: {
          "circle-radius": 4, "circle-color": ["get", "color"],
          "circle-stroke-color": "#ffffff", "circle-stroke-width": 1,
        },
      });
      map.addLayer({
        id: "selected-line", type: "line", source: "selected",
        paint: { "line-color": "#111827", "line-width": 2.4, "line-dasharray": [1.2, 1] },
      });

      const handleZoneClick = (event: maplibregl.MapMouseEvent & { features?: maplibregl.MapGeoJSONFeature[] }) => {
        const id = event.features?.[0]?.properties?.id;
        if (typeof id === "number") onSelectRef.current(id);
      };
      map.on("click", "zone-fill", handleZoneClick);
      map.on("mouseenter", "zone-fill", () => { map.getCanvas().style.cursor = "pointer"; });
      map.on("mouseleave", "zone-fill", () => { map.getCanvas().style.cursor = ""; });
    });

    return () => {
      map.remove();
      mapRef.current = null;
      readyRef.current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lowBandwidth]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !readyRef.current) return;
    const features = zones.map((zone) => ({
      type: "Feature" as const,
      geometry: zone.geometry,
      properties: { id: zone.properties.id, color: zoneColor(zone, colorMode), label: zone.properties.name },
    }));
    (map.getSource("zones") as maplibregl.GeoJSONSource | undefined)?.setData({
      type: "FeatureCollection", features,
    });

    if (!fittedRef.current && features.length) {
      const bounds = new maplibregl.LngLatBounds();
      features.forEach((feature) => {
        const coordinates = (feature.geometry as GeoJSON.Polygon).coordinates[0] as [number, number][];
        coordinates.forEach(([lon, lat]) => bounds.extend([lon, lat]));
      });
      if (!bounds.isEmpty()) {
        map.fitBounds(bounds, { padding: 56, maxZoom: 10.5, duration: 0 });
        fittedRef.current = true;
      }
    }
  }, [zones, colorMode]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !readyRef.current) return;
    const selected = zones.filter((zone) => zone.properties.id === selectedId);
    (map.getSource("selected") as maplibregl.GeoJSONSource | undefined)?.setData({
      type: "FeatureCollection",
      features: selected.map((zone) => ({ type: "Feature", geometry: zone.geometry, properties: {} })),
    });
  }, [selectedId, zones]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !readyRef.current) return;
    const set = (id: string, data?: FeatureCollection | null) => {
      (map.getSource(id) as maplibregl.GeoJSONSource | undefined)?.setData(
        data ?? { type: "FeatureCollection", features: [] },
      );
    };
    set("roads", roads);
    set("assets", assets);
    set("incidents", incidents);
    set("reports", reports);
  }, [roads, assets, incidents, reports]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !readyRef.current) return;
    const visibility = (id: string, visible: boolean) => {
      if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", visible ? "visible" : "none");
    };
    visibility("zone-fill", layers.risk);
    visibility("zone-outline", layers.risk);
    visibility("roads-line", layers.roads);
    visibility("assets-circle", layers.assets);
    visibility("incidents-circle", layers.incidents);
    visibility("reports-circle", layers.reports);
  }, [layers]);

  const legend = colorMode === "susceptibility"
    ? [
        { label: "Very high propensity", color: "rgba(120,53,15,0.75)" },
        { label: "High", color: "rgba(161,98,7,0.7)" },
        { label: "Moderate", color: "rgba(202,138,4,0.6)" },
        { label: "Low", color: "rgba(74,124,89,0.5)" },
      ]
    : (["SAFE", "WATCH", "WARNING", "CRITICAL"] as const).map((level) => ({ label: riskMeta[level].label, color: riskMeta[level].dot }));

  return (
    <div className={className ?? "relative h-full w-full"}>
      <div ref={containerRef} className="h-full w-full" aria-label="Landslide risk map" role="application" />
      <div className="pointer-events-none absolute bottom-6 left-3 z-10 rounded-lg border border-line bg-surface/95 px-2.5 py-2 text-2xs shadow-card">
        <div className="mb-1 font-semibold uppercase tracking-wide text-muted">
          {colorMode === "susceptibility" ? "Terrain propensity (not live hazard)" : "Operational hazard index"}
        </div>
        {legend.map((item) => (
          <div key={item.label} className="flex items-center gap-1.5 py-[1px]">
            <span className="h-2.5 w-3 rounded-sm" style={{ background: item.color }} />
            <span>{item.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
