import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, ClipboardCheck, Languages, Send, XCircle } from "lucide-react";
import clsx from "clsx";
import { api, downloadFile } from "../lib/api";
import { fmtDateTime, fmtNumber, timeAgo } from "../lib/format";
import { LANGUAGES } from "../lib/i18n";
import type { Alert, ZoneCollection } from "../lib/types";
import { useSession } from "../store/session";
import {
  Card, CardHeader, Drawer, EmptyState, ErrorState, Loading, Modal, PriorityBadge, ReasonDialog,
  RiskBadge, StatusBadge, toast,
} from "../components/ui";
import { useFallbackPolling } from "../hooks/useLiveUpdates";
import {
  Table,
  TableHeader,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  Alert as ShadcnAlert,
  AlertDescription as ShadcnAlertDescription,
  Badge as ShadcnBadge,
} from "../components/shadcn";

const STATUSES = ["ALL", "CANDIDATE", "APPROVED", "DELIVERED", "REJECTED", "EXPIRED", "ALL_CLEAR", "CANCELLED"] as const;
type ReasonAction = { kind: "reject" | "cancel" | "all_clear"; alert: Alert };

export default function Alerts() {
  const has = useSession((s) => s.has);
  const [status, setStatus] = useState<(typeof STATUSES)[number]>("ALL");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [approving, setApproving] = useState<Alert | null>(null);
  const [reason, setReason] = useState("");
  const [languages, setLanguages] = useState<string[]>(["en"]);
  const [manualOpen, setManualOpen] = useState(false);
  const [manualZone, setManualZone] = useState("");
  const [manualReason, setManualReason] = useState("");
  const [reasonAction, setReasonAction] = useState<ReasonAction | null>(null);
  const queryClient = useQueryClient();
  const polling = useFallbackPolling(true);

  const alertsQuery = useQuery({
    queryKey: ["alerts", status],
    queryFn: () => api<{ alerts: Alert[]; policy: { approval_required: boolean; note: string } }>(
      `/api/v1/alerts${status === "ALL" ? "" : `?status_filter=${status}`}`,
    ),
    ...polling,
  });

  const zonesQuery = useQuery({
    queryKey: ["risk-zones", "alerts-manual"],
    queryFn: () => api<ZoneCollection>("/api/v1/risk-zones?limit=200"),
    enabled: manualOpen,
  });

  const alerts = alertsQuery.data?.alerts ?? [];
  const selected = useMemo(() => alerts.find((alert) => alert.id === selectedId) ?? null, [alerts, selectedId]);

  const invalidate = () => queryClient.invalidateQueries();
  const approve = useMutation({
    mutationFn: () => api(`/api/v1/alerts/${approving?.id}/approve`, {
      method: "POST", json: { reason, languages },
    }),
    onSuccess: () => {
      toast("Alert approved. Delivery results recorded per channel and language.", "ok");
      setApproving(null); setReason(""); setLanguages(["en"]); invalidate();
    },
    onError: (error) => toast(error instanceof Error ? error.message : "Approval failed", "error"),
  });
  const reject = useMutation({
    mutationFn: ({ id, text }: { id: number; text: string }) => api(`/api/v1/alerts/${id}/reject`, { method: "POST", json: { reason: text } }),
    onSuccess: () => { toast("Alert rejected", "ok"); setSelectedId(null); invalidate(); },
    onError: (error) => toast(error instanceof Error ? error.message : "Rejection failed", "error"),
  });
  const cancel = useMutation({
    mutationFn: ({ id, text, allClear }: { id: number; text: string; allClear: boolean }) =>
      api(`/api/v1/alerts/${id}/cancel`, { method: "POST", json: { reason: text, all_clear: allClear } }),
    onSuccess: () => { toast("Alert closed", "ok"); setSelectedId(null); invalidate(); },
    onError: (error) => toast(error instanceof Error ? error.message : "Cancellation failed", "error"),
  });
  const manual = useMutation({
    mutationFn: () => api<Alert>("/api/v1/alerts/manual-candidate", {
      method: "POST", json: { zone_id: Number(manualZone), reason: manualReason },
    }),
    onSuccess: () => {
      toast("Authority-initiated candidate created — a separate approver is still required.", "ok");
      setManualOpen(false); setManualReason(""); invalidate();
    },
    onError: (error) => toast(error instanceof Error ? error.message : "Could not create candidate", "error"),
  });

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Alerts</h1>
          <p className="text-sm text-muted">
            Policy generates candidates. A human authority must approve before anything is published.
          </p>
        </div>
        {has("alerts:prepare") ? (
          <button className="btn btn-sm" onClick={() => setManualOpen(true)}>
            <AlertTriangle size={14} /> Raise authority-initiated candidate
          </button>
        ) : null}
      </div>

      <div className="flex flex-wrap gap-1">
        {STATUSES.map((item) => (
          <button
            key={item}
            className={clsx("btn btn-sm", status === item && "border-forest text-forest")}
            onClick={() => setStatus(item)}
            aria-pressed={status === item}
          >
            {item.replaceAll("_", " ")}
          </button>
        ))}
      </div>

      <Card>
        <CardHeader
          title={`${alerts.length} alert${alerts.length === 1 ? "" : "s"}`}
          subtitle={alertsQuery.data?.policy.note ?? "Candidate alerts require approval."}
          icon={<ClipboardCheck size={16} />}
        />
        {alertsQuery.isLoading ? <Loading label="Loading alerts" /> : null}
        {alertsQuery.error ? <div className="p-3"><ErrorState error={alertsQuery.error} onRetry={() => alertsQuery.refetch()} /></div> : null}
        <div className="p-3">
          <ShadcnAlert variant="info" className="text-xs">
            <ShadcnAlertDescription className="flex items-center justify-between">
              <span>{alertsQuery.data?.policy.note ?? "Candidate alerts require human authority approval prior to dissemination."}</span>
              <ShadcnBadge variant="outline" className="text-[10px]">Dual-Authorization Policy</ShadcnBadge>
            </ShadcnAlertDescription>
          </ShadcnAlert>
        </div>
        <div className="table-wrap px-2 pb-2">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Reference</TableHead>
                <TableHead>Severity</TableHead>
                <TableHead>Unit</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Hazard</TableHead>
                <TableHead>Priority</TableHead>
                <TableHead>Created</TableHead>
                <TableHead>Expires</TableHead>
                <TableHead>Deliveries</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {alerts.map((alert) => (
                <TableRow key={alert.id} className="cursor-pointer hover:bg-forest/5 transition-colors" onClick={() => setSelectedId(alert.id)}>
                  <TableCell className="font-mono text-xs font-semibold whitespace-nowrap">{alert.reference}</TableCell>
                  <TableCell><RiskBadge level={alert.severity} /></TableCell>
                  <TableCell>
                    <div className="font-medium text-xs text-ink">{alert.zone_name}</div>
                    <div className="text-[10px] text-muted">{alert.district_name}</div>
                  </TableCell>
                  <TableCell><StatusBadge status={alert.status} /></TableCell>
                  <TableCell className="text-right font-mono font-bold text-xs">{fmtNumber(alert.hazard_index, 0)}</TableCell>
                  <TableCell><PriorityBadge level={alert.priority_level} /></TableCell>
                  <TableCell className="whitespace-nowrap text-xs text-muted">{timeAgo(alert.created_at)}</TableCell>
                  <TableCell className="whitespace-nowrap text-xs text-muted">{fmtDateTime(alert.expires)}</TableCell>
                  <TableCell className="text-[11px] text-muted">
                    {alert.deliveries.length ? (
                      <span className="font-mono">{alert.deliveries.filter((d) => d.status === "DELIVERED").length}/{alert.deliveries.length} sent</span>
                    ) : (
                      <span className="text-muted/60">none</span>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
        {!alerts.length && !alertsQuery.isLoading ? (
          <EmptyState
            title="No alerts in this filter"
            body="Candidates appear when a unit crosses the warning threshold and the policy gates pass. Nothing is ever published automatically."
          />
        ) : null}
      </Card>

      <Drawer
        open={selected !== null}
        onClose={() => setSelectedId(null)}
        title={selected?.headline ?? "Alert"}
        subtitle={selected ? `${selected.reference} · ${selected.policy_version} · ${selected.template_version}` : undefined}
        footer={selected ? (
          <div className="flex flex-wrap items-center gap-2">
            {selected.status === "CANDIDATE" && has("alerts:approve") ? (
              <button className="btn btn-primary btn-sm" onClick={() => { setApproving(selected); setReason(""); }}>
                <CheckCircle2 size={14} /> Review & approve
              </button>
            ) : null}
            {["CANDIDATE", "APPROVED"].includes(selected.status) && has("alerts:approve") ? (
              <button className="btn btn-sm" onClick={() => setReasonAction({ kind: "reject", alert: selected })}><XCircle size={14} /> Reject</button>
            ) : null}
            {["APPROVED", "DELIVERED"].includes(selected.status) && has("alerts:cancel") ? (
              <>
                <button className="btn btn-sm" onClick={() => setReasonAction({ kind: "all_clear", alert: selected })}>All-clear</button>
                <button className="btn btn-danger btn-sm" onClick={() => setReasonAction({ kind: "cancel", alert: selected })}>Cancel alert</button>
              </>
            ) : null}
          </div>
        ) : undefined}
      >
        {selected ? (
          <div className="space-y-4 px-4 py-3">
            <div className="flex flex-wrap items-center gap-2">
              <RiskBadge level={selected.severity} size="lg" />
              <StatusBadge status={selected.status} />
              <PriorityBadge level={selected.priority_level} showLabel />
              <span className="chip">Hazard {fmtNumber(selected.hazard_index, 0)} / 100 (index)</span>
            </div>
            <div>
              <div className="eyebrow">Reason</div>
              <p className="mt-1 text-sm leading-relaxed">{selected.reason}</p>
            </div>
            <div>
              <div className="eyebrow">Instructions</div>
              <p className="mt-1 whitespace-pre-line text-sm leading-relaxed">{selected.instructions}</p>
            </div>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div><div className="kpi-label">Onset</div>{fmtDateTime(selected.onset)}</div>
              <div><div className="kpi-label">Expires</div>{fmtDateTime(selected.expires)}</div>
              <div><div className="kpi-label">Approved</div>{fmtDateTime(selected.approved_at)}</div>
              <div><div className="kpi-label">Language</div>{selected.language}</div>
            </div>
            <div>
              <div className="eyebrow">Threatened assets</div>
              {selected.threatened_assets.length ? (
                <ul className="mt-1 space-y-0.5 text-xs">
                  {selected.threatened_assets.map((asset, index) => (
                    <li key={`${asset.name}-${index}`}>{asset.name} <span className="text-muted">({asset.kind}{asset.distance_km ? `, ${asset.distance_km} km` : ""})</span></li>
                  ))}
                </ul>
              ) : <p className="text-xs text-muted">None identified in the exposure buffer.</p>}
            </div>
            <div>
              <div className="eyebrow">Delivery tracking</div>
              <div className="mt-1 space-y-1">
                {selected.deliveries.map((delivery, index) => (
                  <div key={`${delivery.channel}-${delivery.language}-${index}`} className="flex items-start justify-between gap-2 rounded border border-line px-2 py-1 text-2xs">
                    <div>
                      <span className="font-semibold uppercase">{delivery.channel}</span> · {delivery.language}
                      <div className="text-muted">{delivery.detail}</div>
                    </div>
                    <StatusBadge status={delivery.status} />
                  </div>
                ))}
                {!selected.deliveries.length ? <p className="text-xs text-muted">No delivery attempts yet.</p> : null}
              </div>
            </div>
            <div className="rounded-lg border border-line bg-surface-2 p-3 text-xs">
              <div className="flex items-center gap-1.5 font-semibold"><Languages size={14} /> Translation policy</div>
              <p className="mt-1 text-muted">
                Only the English template is marked reviewed in this build. Hindi, Assamese, Bengali and Nepali
                drafts are blocked from delivery until a native reviewer approves them — the API records the block.
              </p>
            </div>
            <div>
              <div className="eyebrow">Source</div>
              <p className="text-xs text-muted">{selected.source}</p>
            </div>
            <p className="rounded-lg border border-line bg-canvas p-3 text-2xs text-muted">{selected.disclaimer}</p>
            <button
              className="btn btn-sm"
              onClick={() => downloadFile(`/api/v1/alerts/${selected.id}/cap`, `${selected.reference}-cap.json`).catch(() => toast("Could not download the CAP draft", "error"))}
            >
              Download CAP-shaped draft
            </button>
          </div>
        ) : null}
      </Drawer>

      <Modal
        open={approving !== null}
        onClose={() => setApproving(null)}
        title="Approve and publish alert"
        footer={
          <>
            <button className="btn btn-sm" onClick={() => setApproving(null)}>Cancel</button>
            <button className="btn btn-primary btn-sm" disabled={reason.trim().length < 8 || approve.isPending} onClick={() => approve.mutate()}>
              <Send size={14} /> {approve.isPending ? "Recording…" : "Approve"}
            </button>
          </>
        }
      >
        <div className="space-y-3 text-sm">
          <p className="text-xs text-muted">
            Approval publishes to the recorded channels only. SMS is blocked (no DLT provider configured) and email is
            queued without a provider. Nothing is sent to the public beyond the approved advisory feed.
          </p>
          <div>
            <label className="label" htmlFor="approve-reason">Approval reason (required, audited)</label>
            <textarea id="approve-reason" className="textarea" rows={3} value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Basis for approval — e.g. verified rainfall, field confirmation, district control-room decision" />
          </div>
          <div>
            <div className="label">Languages</div>
            <div className="flex flex-wrap gap-2">
              {LANGUAGES.map((language) => (
                <label key={language.code} className="flex items-center gap-1.5 rounded-md border border-line px-2 py-1 text-xs">
                  <input
                    type="checkbox"
                    checked={languages.includes(language.code)}
                    onChange={(event) => setLanguages((current) => event.target.checked ? [...current, language.code] : current.filter((code) => code !== language.code))}
                  />
                  {language.label}
                  {!language.reviewed ? <span className="chip border-watch/40 text-watch">unreviewed</span> : null}
                </label>
              ))}
            </div>
          </div>
          <p className="rounded-lg border border-watch/40 bg-watch/5 p-2 text-2xs text-watch">
            Critical and public-facing alerts always require this human approval step. The model cannot publish.
          </p>
        </div>
      </Modal>

      <Modal
        open={manualOpen}
        onClose={() => setManualOpen(false)}
        title="Authority-initiated candidate"
        footer={
          <>
            <button className="btn btn-sm" onClick={() => setManualOpen(false)}>Cancel</button>
            <button className="btn btn-primary btn-sm" disabled={!manualZone || manualReason.trim().length < 15 || manual.isPending} onClick={() => manual.mutate()}>
              Create candidate
            </button>
          </>
        }
      >
        <div className="space-y-3">
          <p className="text-xs text-muted">
            Use this when an authority has information the model does not (for example a phone report from a
            sarpanch). It creates a pending candidate only; a different approver must still publish it.
          </p>
          <div>
            <label className="label" htmlFor="manual-zone">Unit</label>
            <select id="manual-zone" className="select" value={manualZone} onChange={(event) => setManualZone(event.target.value)}>
              <option value="">Select a unit…</option>
              {(zonesQuery.data?.features ?? []).map((zone) => (
                <option key={zone.properties.id} value={zone.properties.id}>
                  {zone.properties.name} · {zone.properties.district_name} · hazard {fmtNumber(zone.properties.hazard_index, 0)}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label" htmlFor="manual-reason">Basis (min 15 characters)</label>
            <textarea id="manual-reason" className="textarea" rows={3} value={manualReason} onChange={(event) => setManualReason(event.target.value)} />
          </div>
        </div>
      </Modal>

      <ReasonDialog
        open={reasonAction !== null}
        onClose={() => setReasonAction(null)}
        title={reasonAction?.kind === "reject" ? "Reject candidate" : reasonAction?.kind === "all_clear" ? "Publish all-clear" : "Cancel alert"}
        description={
          reasonAction?.kind === "reject"
            ? "Rejection closes the candidate without publishing anything. The reason is written to the audit trail."
            : reasonAction?.kind === "all_clear"
              ? "An all-clear tells the public the advisory has ended. It is published like any other advisory and is audited."
              : "Cancelling withdraws the advisory. The reason is written to the audit trail."
        }
        confirmLabel={reasonAction?.kind === "reject" ? "Reject" : reasonAction?.kind === "all_clear" ? "Publish all-clear" : "Cancel alert"}
        busy={reject.isPending || cancel.isPending}
        onConfirm={(text) => {
          if (!reasonAction) return;
          if (reasonAction.kind === "reject") reject.mutate({ id: reasonAction.alert.id, text });
          else cancel.mutate({ id: reasonAction.alert.id, text, allClear: reasonAction.kind === "all_clear" });
          setReasonAction(null);
        }}
      />
    </div>
  );
}
