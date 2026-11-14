import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { CheckCircle2, Eye, RefreshCw, Satellite, XCircle } from "lucide-react";
import { api } from "../lib/api";
import {
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
  Button,
} from "../components/shadcn";

interface SatelliteDetection {
  id: number;
  district_code: string;
  satellite_source: string;
  baseline_date: string;
  detection_date: string;
  ndvi_drop_pct: number;
  disturbance_area_m2: number;
  scar_lat: number;
  scar_lon: number;
  confidence_score: number;
  status: "UNVERIFIED_CANDIDATE" | "VERIFIED_LANDSLIDE" | "FALSE_POSITIVE" | "INVESTIGATION_REQUIRED";
  notes: string;
  geometry_json: any;
}

export default function SatelliteChange() {
  const [district, setDistrict] = useState<string>("ALL");
  const [selectedDetection, setSelectedDetection] = useState<SatelliteDetection | null>(null);

  const { data, isLoading, refetch } = useQuery<{
    count: number;
    detections: SatelliteDetection[];
    verification_rule: string;
  }>({
    queryKey: ["satellite-detections", district],
    queryFn: () =>
      api(
        `/api/v1/satellite/detections${district !== "ALL" ? `?district_code=${district}` : ""}`
      ),
  });

  const verifyMutation = useMutation<any, Error, { id: number; decision: string; notes: string }>({
    mutationFn: ({ id, decision, notes }) =>
      api(`/api/v1/satellite/detections/${id}/verify`, {
        method: "PATCH",
        body: JSON.stringify({ decision, verification_notes: notes }),
      }),
    onSuccess: () => {
      refetch();
      setSelectedDetection(null);
    },
  });

  const detections = data?.detections ?? [];

  return (
    <div className="space-y-6">
      {/* Header and Disclosures */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 pb-2 border-b border-line">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="flex items-center gap-1.5 text-[11px] font-semibold text-forest bg-forest-soft border border-forest/25 px-2.5 py-0.5 rounded-full">
              <Satellite size={12} />
              Multi-Spectral Earth Observation
            </span>
            <DisclosurePill
              text="Sentinel-2 10m & PlanetScope 3m Orthorectified Change Detection"
              tooltip="Differential vegetation indexing (dNDVI) identifies slope scars; platform protocol mandates human verification before publishing any official landslide record."
            />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-ink">
            Satellite-Based Change Detection Pipeline
          </h1>
          <p className="text-xs text-muted mt-0.5">
            Multi-spectral Earth observation analytics: Sentinel-2 and PlanetScope vegetation loss (NDVI), slope scarp emergence, and candidate landslide detection.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <ShimmerButton
            variant="secondary"
            onClick={() => refetch()}
            className="text-xs"
          >
            <RefreshCw size={13} className={isLoading ? "animate-spin" : ""} />
            Sync Constellation
          </ShimmerButton>
        </div>
      </div>

      {/* District Segmented Controller */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <SegmentedControl
          options={[
            { value: "ALL", label: "Statewide (All Passes)" },
            { value: "AS-KMR", label: "Kamrup Metro (Assam)" },
            { value: "ML-EKH", label: "East Khasi Hills (Meghalaya)" },
            { value: "MZ-AIZ", label: "Aizawl (Mizoram)" },
          ]}
          value={district}
          onChange={setDistrict}
        />
        <div className="text-[11px] text-muted">
          Change Candidates in Feed: <strong className="text-ink font-mono">{detections.length}</strong>
        </div>
      </div>

      {/* Safety Protocol Banner */}
      <Alert variant="warning" className="rounded-2xl border-warning/30 bg-surface-2/80 dark:bg-surface-2/50 backdrop-blur-md">
        <div className="space-y-1">
          <AlertTitle className="text-xs font-semibold text-ink">
            Strict Scientific Validation Protocol
          </AlertTitle>
          <AlertDescription className="text-xs text-muted leading-relaxed">
            {data?.verification_rule ??
              "MANDATORY: Satellite detections are NEVER auto-promoted to confirmed landslides without on-ground inspection or analyst review."}
          </AlertDescription>
        </div>
      </Alert>

      {/* Detections List & Verification Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          <SpotlightCard>
            <div className="flex items-center justify-between pb-3 mb-3 border-b border-line">
              <div className="flex items-center gap-2">
                <div className="p-2 rounded-xl bg-forest-soft text-forest">
                  <Satellite size={16} />
                </div>
                <div>
                  <h3 className="font-bold text-xs uppercase tracking-wider text-ink">
                    Detected Slope Disturbance Candidates
                  </h3>
                  <p className="text-[11px] text-muted">
                    Automated change detection flagged from recent cloud-free satellite passes
                  </p>
                </div>
              </div>
            </div>

            <div className="space-y-3">
              {detections.length === 0 ? (
                <div className="text-center py-8 text-muted text-xs">
                  No candidate anomalies identified in recent cloud-free acquisitions.
                </div>
              ) : (
                detections.map((det) => (
                  <div
                    key={det.id}
                    onClick={() => setSelectedDetection(det)}
                    className={`p-4 rounded-2xl border text-xs cursor-pointer transition-all duration-200 ${
                      selectedDetection?.id === det.id
                        ? "bg-forest/10 border-forest text-ink shadow-sm"
                        : "bg-surface-2/70 dark:bg-surface-2/40 border-line hover:border-forest/40"
                    }`}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line/60 pb-2.5 mb-2.5">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-ink">Candidate #{det.id}</span>
                        <span className="text-[10px] text-muted font-mono uppercase">[{det.district_code}]</span>
                        <Badge
                          variant={
                            det.status === "VERIFIED_LANDSLIDE"
                              ? "destructive"
                              : det.status === "UNVERIFIED_CANDIDATE"
                              ? "warning"
                              : "success"
                          }
                        >
                          {det.status.replace("_", " ")}
                        </Badge>
                      </div>
                      <div className="font-mono text-muted text-[11px]">
                        Confidence: <strong className="text-forest">{det.confidence_score}%</strong>
                      </div>
                    </div>

                    <p className="text-xs text-ink font-medium leading-relaxed">{det.notes}</p>

                    <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-2 text-[11px] text-muted bg-surface-3/70 dark:bg-surface-3/40 p-2.5 rounded-xl border border-line/50">
                      <div>Satellite: <strong className="text-ink">{det.satellite_source.split(" ")[0]}</strong></div>
                      <div>NDVI Drop: <strong className="text-critical font-mono">-{det.ndvi_drop_pct}%</strong></div>
                      <div>Scar Area: <strong className="text-ink font-mono">{det.disturbance_area_m2} m²</strong></div>
                      <div>Coords: <strong className="font-mono text-ink">{det.scar_lat.toFixed(3)}, {det.scar_lon.toFixed(3)}</strong></div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </SpotlightCard>
        </div>

        {/* Human-in-the-Loop Verification Action Panel */}
        <div>
          <SpotlightCard>
            <div className="flex items-center justify-between pb-3 mb-3 border-b border-line">
              <div className="flex items-center gap-2">
                <div className="p-2 rounded-xl bg-forest-soft text-forest">
                  <Eye size={16} />
                </div>
                <div>
                  <h3 className="font-bold text-xs uppercase tracking-wider text-ink">
                    Analyst Verification Panel
                  </h3>
                  <p className="text-[11px] text-muted">
                    Review and certify Earth observation findings
                  </p>
                </div>
              </div>
            </div>

            <div className="space-y-4 text-xs">
              {selectedDetection ? (
                <div className="space-y-4">
                  <div>
                    <span className="text-muted block text-[10px] uppercase font-semibold">Selected Target:</span>
                    <h3 className="font-bold text-ink text-sm mt-0.5">
                      Candidate #{selectedDetection.id} ({selectedDetection.district_code})
                    </h3>
                    <div className="text-[11px] text-muted mt-1 font-mono">
                      Sensor: {selectedDetection.satellite_source}
                    </div>
                  </div>

                  <div className="p-3.5 bg-surface-2/70 dark:bg-surface-2/40 rounded-xl border border-line space-y-1.5">
                    <div className="font-bold text-ink">Spectral Anomaly Breakdown</div>
                    <div>NDVI Loss: <strong className="text-critical font-mono">-{selectedDetection.ndvi_drop_pct}%</strong></div>
                    <div>Scar Area: <strong className="font-mono">{selectedDetection.disturbance_area_m2} m²</strong></div>
                    <div>Pass Date: <strong className="font-mono">{selectedDetection.detection_date}</strong></div>
                  </div>

                  <div className="space-y-2.5 pt-2">
                    <ShimmerButton
                      onClick={() =>
                        verifyMutation.mutate({
                          id: selectedDetection.id,
                          decision: "VERIFIED_LANDSLIDE",
                          notes: "Crown scarp and debris tongue confirmed against high-resolution imagery pass.",
                        })
                      }
                      disabled={verifyMutation.isPending}
                      variant="primary"
                      className="w-full text-xs py-2.5"
                    >
                      <CheckCircle2 size={13} /> Confirm as Landslide Incident
                    </ShimmerButton>

                    <Button
                      variant="outline"
                      onClick={() =>
                        verifyMutation.mutate({
                          id: selectedDetection.id,
                          decision: "FALSE_POSITIVE",
                          notes: "Disturbance caused by routine agricultural terracing / cloud shadow.",
                        })
                      }
                      disabled={verifyMutation.isPending}
                      className="w-full text-xs py-2 h-auto"
                    >
                      <XCircle size={13} /> Classify as False Positive
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="text-center py-10 text-muted">
                  Select a satellite detection candidate on the left to review spectral anomalies and submit human verification.
                </div>
              )}
            </div>
          </SpotlightCard>
        </div>
      </div>
    </div>
  );
}
