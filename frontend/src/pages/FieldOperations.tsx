import { useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Camera, CheckCircle2, CloudOff, Crosshair, RefreshCw, Route, Send, Smartphone, Wifi, WifiOff,
} from "lucide-react";
import clsx from "clsx";
import { api, qs } from "../lib/api";
import { fmtDateTime, fmtNumber, timeAgo } from "../lib/format";
import type { Assignment, RoadSegment } from "../lib/types";
import { useSession } from "../store/session";
import { useUi } from "../store/ui";
import { Card, EmptyState, PriorityBadge, RiskBadge, StatusBadge, Tabs, toast } from "../components/ui";
import { enqueueReport, getMeta, listQueuedReports, markReport, setLastSynced, type QueuedReport } from "../lib/offline";

type Tab = "report" | "queue" | "roads" | "units";

const HAZARDS = [
  ["GROUND_CRACK", "Ground cracks"],
  ["SLOPE_MOVEMENT", "Slope movement"],
  ["ROCKFALL", "Rockfall"],
  ["ROAD_BLOCKAGE", "Road blockage"],
  ["DEBRIS_FLOW", "Debris flow"],
  ["SUBSIDENCE", "Subsidence"],
  ["OTHER", "Other"],
];

export default function FieldOperations() {
  const user = useSession((s) => s.user);
  const lowBandwidth = useUi((s) => s.lowBandwidth);
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<Tab>("report");
  const [online, setOnline] = useState(navigator.onLine);
  const [queue, setQueue] = useState<QueuedReport[]>([]);
  const [lastSynced, setLastSyncedState] = useState<string | null>(null);
  const [deviceId, setDeviceId] = useState("");
  const [hazardType, setHazardType] = useState("GROUND_CRACK");
  const [description, setDescription] = useState("");
  const [gps, setGps] = useState<{ lat: number; lon: number; accuracy: number } | null>(null);
  const [gpsError, setGpsError] = useState<string | null>(null);
  const [consent, setConsent] = useState(false);
  const [photo, setPhoto] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [roadDraft, setRoadDraft] = useState<Record<number, { status: string; evidence: string }>>({});

  const refreshQueue = async () => {
    const rows = await listQueuedReports();
    setQueue(rows);
    const meta = await getMeta();
    setLastSyncedState(meta.last_synced);
    setDeviceId(meta.device_id);
  };

  useEffect(() => {
    refreshQueue();
    const goOnline = () => setOnline(true);
    const goOffline = () => setOnline(false);
    window.addEventListener("online", goOnline);
    window.addEventListener("offline", goOffline);
    return () => {
      window.removeEventListener("online", goOnline);
      window.removeEventListener("offline", goOffline);
    };
  }, []);

  const assignments = useQuery({
    queryKey: ["response", "mine", user?.id],
    queryFn: () => api<{ assignments: Assignment[] }>(`/api/v1/response${qs({ assigned_to: user?.id })}`),
    enabled: Boolean(user?.id),
  });
  const roads = useQuery({
    queryKey: ["roads", "field"],
    queryFn: () => api<{ roads: Array<{ id: number; ref: string; name: string; segments: RoadSegment[] }> }>("/api/v1/roads"),
    enabled: tab === "roads",
  });

  const pendingCount = queue.filter((item) => !item.synced).length;

  const locate = () => {
    setGpsError(null);
    if (!navigator.geolocation) {
      setGpsError("This device does not expose geolocation.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) => setGps({ lat: position.coords.latitude, lon: position.coords.longitude, accuracy: position.coords.accuracy }),
      (error) => setGpsError(error.message),
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 30000 },
    );
  };

  const resetForm = () => {
    setDescription("");
    setPhoto(null);
    setConsent(false);
    setGps(null);
  };

  const submit = async () => {
    if (!consent) { toast("Consent is required to store location and media.", "error"); return; }
    setBusy(true);
    const payload = {
      client_uuid: crypto.randomUUID(),
      hazard_type: hazardType,
      description,
      lat: gps?.lat,
      lon: gps?.lon,
      gps_accuracy_m: gps?.accuracy,
      observed_at: new Date().toISOString(),
      consent,
      anonymous: false,
      device_id: deviceId,
      reporter_name: user?.name,
    };
    try {
      if (online) {
        const form = new FormData();
        Object.entries(payload).forEach(([key, value]) => {
          if (value !== undefined && value !== null) form.append(key, String(value));
        });
        if (photo) form.append("files", photo);
        await api("/api/v1/reports", { method: "POST", body: form });
        toast("Report submitted and pending officer verification.", "ok");
      } else {
        await enqueueReport(payload);
        toast("Offline: report queued on this device. It is not synced yet.", "info");
      }
      resetForm();
      await refreshQueue();
      queryClient.invalidateQueries();
    } catch (error) {
      await enqueueReport(payload);
      toast(error instanceof Error ? `${error.message} — kept in the offline queue.` : "Queued for retry.", "error");
      await refreshQueue();
    } finally {
      setBusy(false);
    }
  };

  const syncQueue = async () => {
    const pending = queue.filter((item) => !item.synced);
    if (!pending.length) { toast("Nothing to sync.", "info"); return; }
    setBusy(true);
    try {
      const response = await api<{ accepted: number; duplicates: number; failed: number; results: Array<{ client_uuid: string; status: string; id?: number; error?: string }> }>(
        "/api/v1/reports/sync",
        { method: "POST", json: { items: pending.map((item) => item.payload) } },
      );
      const byUuid = new Map(response.results.map((result) => [result.client_uuid, result]));
      for (const item of pending) {
        const result = byUuid.get(item.client_uuid);
        if (result && (result.status === "accepted" || result.status === "duplicate")) {
          item.synced = true;
          item.server_id = result.id ?? null;
          item.error = null;
        } else {
          item.error = result?.error ?? "Server rejected this item";
        }
        await markReport(item);
      }
      await setLastSynced();
      await refreshQueue();
      toast(`Synced ${response.accepted + response.duplicates}, failed ${response.failed}.`, response.failed ? "error" : "ok");
      queryClient.invalidateQueries();
    } catch (error) {
      toast(error instanceof Error ? error.message : "Sync failed — queue retained.", "error");
    } finally {
      setBusy(false);
    }
  };

  const saveRoad = async (segment: RoadSegment) => {
    const draft = roadDraft[segment.id];
    if (!draft?.evidence || draft.evidence.trim().length < 4) {
      toast("Evidence is required for a road status update.", "error");
      return;
    }
    try {
      await api(`/api/v1/roads/segments/${segment.id}/status`, {
        method: "PATCH",
        json: { status: draft.status ?? segment.status, status_source: "OFFICER_VERIFIED", evidence: draft.evidence },
      });
      toast("Road status updated with officer verification.", "ok");
      queryClient.invalidateQueries();
    } catch (error) {
      toast(error instanceof Error ? error.message : "Update failed", "error");
    }
  };

  const myAssignments = assignments.data?.assignments ?? [];
  const segments = useMemo(() => (roads.data?.roads ?? []).flatMap((road) => road.segments.map((segment) => ({ ...segment, roadName: `${road.ref} — ${road.name}` }))), [roads.data]);

  return (
    <div className="mx-auto max-w-4xl space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Field Operations</h1>
          <p className="text-sm text-muted">Offline-capable reporting for authorised officers.</p>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          <span className={clsx("chip", online ? "border-safe/40 text-safe" : "border-critical/40 text-critical")}>
            {online ? <Wifi size={12} /> : <WifiOff size={12} />} {online ? "ONLINE" : "OFFLINE"}
          </span>
          <span className="chip"><Smartphone size={12} /> {pendingCount} queued</span>
          <span className="chip">Last sync: {lastSynced ? timeAgo(lastSynced) : "never"}</span>
        </div>
      </div>

      {lowBandwidth ? (
        <div className="rounded-lg border border-watch/40 bg-watch/5 px-3 py-2 text-xs text-watch">
          Low-bandwidth mode is on: no basemap tiles and reduced imagery.
        </div>
      ) : null}

      <Card>
        <Tabs
          tabs={[
            { id: "report", label: "Report hazard" },
            { id: "queue", label: `Offline queue (${pendingCount})` },
            { id: "roads", label: "Road status" },
            { id: "units", label: "My assignments" },
          ]}
          active={tab}
          onChange={setTab}
        />
        <div className="p-3">
          {tab === "report" ? (
            <div className="space-y-3">
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <label className="label" htmlFor="hazard">Hazard type</label>
                  <select id="hazard" className="select" value={hazardType} onChange={(event) => setHazardType(event.target.value)}>
                    {HAZARDS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                  </select>
                </div>
                <div>
                  <span className="label">Location</span>
                  <div className="flex items-center gap-2">
                    <button className="btn btn-lg flex-1" onClick={locate} type="button"><Crosshair size={16} /> Use GPS</button>
                    {gps ? <span className="text-2xs text-muted">{gps.lat.toFixed(4)}, {gps.lon.toFixed(4)} · ±{Math.round(gps.accuracy)} m</span> : null}
                  </div>
                  {gpsError ? <p className="mt-1 text-2xs text-critical">{gpsError}</p> : null}
                </div>
              </div>
              <div>
                <label className="label" htmlFor="description">What did you observe?</label>
                <textarea id="description" className="textarea" rows={3} value={description} onChange={(event) => setDescription(event.target.value)} placeholder="e.g. Continuous tension crack ~12 m long above the road cut, fresh soil exposed" />
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <label className="btn btn-lg cursor-pointer">
                  <Camera size={16} /> {photo ? photo.name.slice(0, 24) : "Add photo"}
                  <input type="file" accept="image/*" capture="environment" className="hidden" onChange={(event) => setPhoto(event.target.files?.[0] ?? null)} />
                </label>
                <span className="text-2xs text-muted">JPEG/PNG/WebP up to 10 MB</span>
              </div>
              <label className="flex items-start gap-2 rounded-lg border border-line bg-surface-2 p-2.5 text-xs">
                <input type="checkbox" className="mt-0.5" checked={consent} onChange={(event) => setConsent(event.target.checked)} />
                <span>I consent to sharing this location and photo with the district authority for verification. Data is used only for disaster response.</span>
              </label>
              <button className="btn btn-primary btn-lg w-full" onClick={submit} disabled={busy || !consent}>
                <Send size={16} /> {busy ? "Submitting…" : online ? "Submit report" : "Queue report offline"}
              </button>
              <p className="hint">
                Reports enter <b>PENDING VERIFICATION</b> and never change hazard until an officer verifies them.
                A report is marked synchronized only after the server returns an id.
              </p>
            </div>
          ) : null}

          {tab === "queue" ? (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <p className="text-xs text-muted">{queue.length} local reports · {pendingCount} awaiting sync</p>
                <button className="btn btn-sm" onClick={syncQueue} disabled={busy || !online || !pendingCount}>
                  <RefreshCw size={14} className={busy ? "animate-spin" : ""} /> Sync now
                </button>
              </div>
              {queue.map((item) => (
                <div key={item.client_uuid} className="rounded-lg border border-line px-3 py-2 text-xs">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-medium">{String(item.payload.hazard_type).replaceAll("_", " ")}</span>
                    {item.synced ? (
                      <span className="badge border-safe/40 text-safe bg-safe/10"><CheckCircle2 size={11} /> SYNCED · id {item.server_id}</span>
                    ) : (
                      <span className="badge border-watch/40 text-watch bg-watch/10">{online ? "READY" : "OFFLINE"}</span>
                    )}
                  </div>
                  <div className="mt-1 text-muted">{String(item.payload.description ?? "")}</div>
                  <div className="mt-1 flex flex-wrap gap-2 text-2xs text-muted">
                    <span>{fmtDateTime(item.created_at)}</span>
                    <span className="mono">{item.client_uuid.slice(0, 12)}</span>
                    {item.error ? <span className="text-critical">{item.error}</span> : null}
                  </div>
                </div>
              ))}
              {!queue.length ? <EmptyState icon={<CloudOff size={18} />} title="Queue is empty" body="Reports captured without connectivity appear here with their client-generated id." /> : null}
            </div>
          ) : null}

          {tab === "roads" ? (
            <div className="space-y-2">
              <p className="text-xs text-muted">Officer-verified status is distinct from model-estimated risk. Evidence is mandatory.</p>
              {segments.map((segment) => (
                <div key={segment.id} className="rounded-lg border border-line px-3 py-2">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <div className="text-xs font-medium">{segment.roadName}</div>
                      <div className="text-2xs text-muted">{segment.name} · {fmtNumber(segment.length_km, 1)} km</div>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <StatusBadge status={segment.status} />
                      <span className="chip">{segment.status_source.replaceAll("_", " ")}</span>
                    </div>
                  </div>
                  <div className="mt-2 flex flex-wrap items-center gap-1.5">
                    <select
                      className="select w-auto"
                      value={roadDraft[segment.id]?.status ?? segment.status}
                      onChange={(event) => setRoadDraft((current) => ({ ...current, [segment.id]: { status: event.target.value, evidence: current[segment.id]?.evidence ?? "" } }))}
                      aria-label={`Status for ${segment.name}`}
                    >
                      {["OPEN", "RESTRICTED", "AT_RISK", "BLOCKED"].map((value) => <option key={value} value={value}>{value}</option>)}
                    </select>
                    <input
                      className="input flex-1"
                      placeholder="Evidence (required)"
                      value={roadDraft[segment.id]?.evidence ?? ""}
                      onChange={(event) => setRoadDraft((current) => ({ ...current, [segment.id]: { status: current[segment.id]?.status ?? segment.status, evidence: event.target.value } }))}
                    />
                    <button className="btn btn-sm" onClick={() => saveRoad(segment)}><Route size={14} /> Save</button>
                  </div>
                </div>
              ))}
              {!segments.length && !roads.isLoading ? <EmptyState title="No segments in your scope" /> : null}
            </div>
          ) : null}

          {tab === "units" ? (
            <div className="space-y-2">
              {myAssignments.map((assignment) => (
                <div key={assignment.id} className="rounded-lg border border-line px-3 py-2">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="text-sm font-medium">{assignment.zone_name}</span>
                    <div className="flex items-center gap-1.5">
                      <PriorityBadge level={assignment.priority} />
                      <StatusBadge status={assignment.status} />
                    </div>
                  </div>
                  <div className="mt-1 flex items-center gap-2">
                    <RiskBadge level={assignment.hazard_level} index={assignment.hazard_index} />
                    <span className="text-2xs text-muted">Exposure {fmtNumber(assignment.exposure_score, 0)} · updated {timeAgo(assignment.updated_at)}</span>
                  </div>
                  <p className="mt-1 text-xs text-muted">{assignment.recommended_action}</p>
                </div>
              ))}
              {!myAssignments.length && !assignments.isLoading ? <EmptyState title="No assignments" body="Your district administrator will assign inspections from the Response Center." /> : null}
            </div>
          ) : null}
        </div>
      </Card>

      <p className="text-2xs text-muted">
        Offline support uses a service worker for the app shell and IndexedDB for the report queue. Media captured
        offline stays on the device until connectivity returns; the server is the source of truth for verification.
      </p>
    </div>
  );
}
