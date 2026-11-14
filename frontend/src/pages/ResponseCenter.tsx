import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, ClipboardList, UserPlus } from "lucide-react";
import clsx from "clsx";
import { api, qs } from "../lib/api";
import { fmtNumber, priorityMeta, timeAgo } from "../lib/format";
import type { Assignment, ZoneCollection } from "../lib/types";
import { useSession } from "../store/session";
import { Card, CardHeader, EmptyState, ErrorState, Loading, Modal, PriorityBadge, RiskBadge, StatusBadge, toast } from "../components/ui";
import { useFallbackPolling } from "../hooks/useLiveUpdates";
import {
  Table,
  TableHeader,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  Badge as ShadcnBadge,
} from "../components/shadcn";

const FLOW: Record<string, string[]> = {
  DETECTED: ["REVIEWED", "ASSIGNED"],
  REVIEWED: ["ASSIGNED", "RESOLVED"],
  ASSIGNED: ["INSPECTED", "REVIEWED", "RESOLVED"],
  INSPECTED: ["RESOLVED"],
  RESOLVED: ["REOPENED"],
  REOPENED: ["ASSIGNED", "INSPECTED", "RESOLVED"],
};

export default function ResponseCenter() {
  const has = useSession((s) => s.has);
  const [status, setStatus] = useState("");
  const [editing, setEditing] = useState<Assignment | null>(null);
  const [assigning, setAssigning] = useState(false);
  const [assignZone, setAssignZone] = useState("");
  const [assignOfficer, setAssignOfficer] = useState("");
  const [assignReason, setAssignReason] = useState("");
  const [updateStatus, setUpdateStatus] = useState("");
  const [updatePriority, setUpdatePriority] = useState("");
  const [updateNotes, setUpdateNotes] = useState("");
  const [updateReason, setUpdateReason] = useState("");
  const queryClient = useQueryClient();
  const polling = useFallbackPolling(true);

  const assignments = useQuery({
    queryKey: ["response", status],
    queryFn: () => api<{ assignments: Assignment[]; counts: Record<string, number>; lifecycle: string[] }>(
      `/api/v1/response${qs({ status_filter: status || undefined, limit: 300 })}`,
    ),
    ...polling,
  });
  const users = useQuery({
    queryKey: ["admin-users"],
    queryFn: () => api<{ users: Array<{ id: number; name: string; role: string; role_label: string }> }>("/api/v1/admin/users"),
    enabled: has("users:read"),
  });
  const zones = useQuery({
    queryKey: ["risk-zones", "response"],
    queryFn: () => api<ZoneCollection>("/api/v1/risk-zones?limit=300"),
    enabled: assigning,
  });

  const officers = useMemo(
    () => (users.data?.users ?? []).filter((user) => ["field_officer", "analyst", "district_admin"].includes(user.role)),
    [users.data],
  );

  const invalidate = () => queryClient.invalidateQueries();
  const assign = useMutation({
    mutationFn: () => api("/api/v1/response/assign", {
      method: "POST",
      json: {
        zone_id: Number(assignZone),
        assigned_to: assignOfficer ? Number(assignOfficer) : null,
        reason: assignReason,
      },
    }),
    onSuccess: () => { toast("Response assignment created", "ok"); setAssigning(false); setAssignReason(""); invalidate(); },
    onError: (error) => toast(error instanceof Error ? error.message : "Could not assign", "error"),
  });
  const update = useMutation({
    mutationFn: (assignment: Assignment) => api(`/api/v1/response/${assignment.id}`, {
      method: "PATCH",
      json: {
        status: updateStatus || undefined,
        priority: updatePriority || undefined,
        notes: updateNotes || undefined,
        reason: updateReason,
      },
    }),
    onSuccess: () => { toast("Assignment updated and audited", "ok"); setEditing(null); invalidate(); },
    onError: (error) => toast(error instanceof Error ? error.message : "Update failed", "error"),
  });

  const openEdit = (assignment: Assignment) => {
    setEditing(assignment);
    setUpdateStatus(assignment.status);
    setUpdatePriority(assignment.priority);
    setUpdateNotes(assignment.notes);
    setUpdateReason("");
  };

  const counts = assignments.data?.counts ?? {};
  const list = assignments.data?.assignments ?? [];
  const allowedNext = editing ? FLOW[editing.status] ?? [] : [];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Response Center</h1>
          <p className="text-sm text-muted">Ranked incidents, assignments, escalations and the audit trail.</p>
        </div>
        {has("response:write") ? (
          <button className="btn btn-sm" onClick={() => setAssigning(true)}><UserPlus size={14} /> Assign inspection</button>
        ) : null}
      </div>

      <div className="grid grid-cols-2 gap-2 md:grid-cols-6">
        {Object.entries({ DETECTED: 0, REVIEWED: 0, ASSIGNED: 0, INSPECTED: 0, RESOLVED: 0, REOPENED: 0 }).map(([key]) => (
          <Card key={key} className="px-3 py-2">
            <div className="kpi-label">{key}</div>
            <div className="stat-value">{fmtNumber(counts[key] ?? 0)}</div>
          </Card>
        ))}
      </div>

      <div className="flex flex-wrap gap-1">
        {["", "ASSIGNED", "INSPECTED", "RESOLVED", "REOPENED"].map((value) => (
          <button key={value || "all"} className={clsx("btn btn-sm", status === value && "border-forest text-forest")} onClick={() => setStatus(value)}>
            {value || "All open"}
          </button>
        ))}
      </div>

      <Card>
        <CardHeader
          title="Incident queue"
          subtitle="Lifecycle: DETECTED → REVIEWED → ASSIGNED → INSPECTED → RESOLVED. Priority changes require a reason."
          icon={<ClipboardList size={16} />}
        />
        {assignments.isLoading ? <Loading label="Loading assignments" /> : null}
        {assignments.error ? <div className="p-3"><ErrorState error={assignments.error} onRetry={() => assignments.refetch()} /></div> : null}
        <div className="table-wrap px-2 pb-2">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Priority</TableHead>
                <TableHead>Unit</TableHead>
                <TableHead>Hazard</TableHead>
                <TableHead className="text-right">Exposure</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Officer</TableHead>
                <TableHead>Recommended action</TableHead>
                <TableHead>Updated</TableHead>
                <TableHead className="text-right">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {list.map((assignment) => (
                <TableRow key={assignment.id} className="hover:bg-forest/5 transition-colors">
                  <TableCell><PriorityBadge level={assignment.priority} showLabel /></TableCell>
                  <TableCell>
                    <div className="font-medium text-xs text-ink">{assignment.zone_name}</div>
                    <div className="text-[10px] text-muted">{assignment.district_code} · #{assignment.id}</div>
                  </TableCell>
                  <TableCell><RiskBadge level={assignment.hazard_level} index={assignment.hazard_index} /></TableCell>
                  <TableCell className="text-right font-mono font-semibold text-xs">{fmtNumber(assignment.exposure_score, 0)}</TableCell>
                  <TableCell><StatusBadge status={assignment.status} /></TableCell>
                  <TableCell className="text-xs text-muted">
                    {assignment.assignee_name ? (
                      <span className="text-ink font-medium">{assignment.assignee_name}</span>
                    ) : (
                      <ShadcnBadge variant="secondary" className="text-[10px]">Unassigned</ShadcnBadge>
                    )}
                  </TableCell>
                  <TableCell className="max-w-[280px] text-[11px] text-muted leading-snug">{assignment.recommended_action ?? "—"}</TableCell>
                  <TableCell className="whitespace-nowrap text-xs text-muted">{timeAgo(assignment.updated_at)}</TableCell>
                  <TableCell className="text-right">
                    <button className="btn btn-sm text-xs rounded-full inline-flex items-center gap-1" onClick={() => openEdit(assignment)}>Update <ArrowRight size={12} /></button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
        {!list.length && !assignments.isLoading ? (
          <EmptyState title="Nothing in the queue" body="Assign an inspection from a high-priority unit, or wait for the alert policy to open one." />
        ) : null}
      </Card>

      <Modal
        open={assigning}
        onClose={() => setAssigning(false)}
        title="Assign inspection"
        footer={
          <>
            <button className="btn btn-sm" onClick={() => setAssigning(false)}>Cancel</button>
            <button className="btn btn-primary btn-sm" disabled={!assignZone || assignReason.trim().length < 4 || assign.isPending} onClick={() => assign.mutate()}>
              Create assignment
            </button>
          </>
        }
      >
        <div className="space-y-3">
          <div>
            <label className="label" htmlFor="assign-zone">Risk unit</label>
            <select id="assign-zone" className="select" value={assignZone} onChange={(event) => setAssignZone(event.target.value)}>
              <option value="">Select unit…</option>
              {(zones.data?.features ?? []).map((zone) => (
                <option key={zone.properties.id} value={zone.properties.id}>
                  {zone.properties.name} · hazard {fmtNumber(zone.properties.hazard_index, 0)} · {zone.properties.priority_level}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label" htmlFor="assign-officer">Officer</label>
            <select id="assign-officer" className="select" value={assignOfficer} onChange={(event) => setAssignOfficer(event.target.value)}>
              <option value="">Leave unassigned (detected)</option>
              {officers.map((officer) => <option key={officer.id} value={officer.id}>{officer.name} — {officer.role_label}</option>)}
            </select>
            {!has("users:read") ? <p className="hint mt-1">Your role cannot list users; leave unassigned and a district administrator will assign.</p> : null}
          </div>
          <div>
            <label className="label" htmlFor="assign-reason">Reason (audited)</label>
            <textarea id="assign-reason" className="textarea" rows={2} value={assignReason} onChange={(event) => setAssignReason(event.target.value)} />
          </div>
        </div>
      </Modal>

      <Modal
        open={editing !== null}
        onClose={() => setEditing(null)}
        title={editing ? `Update #${editing.id} — ${editing.zone_name}` : "Update"}
        footer={
          <>
            <button className="btn btn-sm" onClick={() => setEditing(null)}>Cancel</button>
            <button className="btn btn-primary btn-sm" disabled={update.isPending} onClick={() => editing && update.mutate(editing)}>Save</button>
          </>
        }
      >
        {editing ? (
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <StatusBadge status={editing.status} />
              <span className="text-muted">Allowed next: {allowedNext.join(", ") || "none"}</span>
            </div>
            <div>
              <label className="label" htmlFor="update-status">Status</label>
              <select id="update-status" className="select" value={updateStatus} onChange={(event) => setUpdateStatus(event.target.value)}>
                <option value={editing.status}>{editing.status} (no change)</option>
                {allowedNext.map((next) => <option key={next} value={next}>{next}</option>)}
              </select>
            </div>
            <div>
              <label className="label" htmlFor="update-priority">Priority</label>
              <select id="update-priority" className="select" value={updatePriority} onChange={(event) => setUpdatePriority(event.target.value)}>
                {Object.entries(priorityMeta).map(([key, meta]) => <option key={key} value={key}>{key} — {meta.label}</option>)}
              </select>
            </div>
            <div>
              <label className="label" htmlFor="update-notes">Field notes</label>
              <textarea id="update-notes" className="textarea" rows={2} value={updateNotes} onChange={(event) => setUpdateNotes(event.target.value)} />
            </div>
            <div>
              <label className="label" htmlFor="update-reason">Reason {updatePriority !== editing.priority ? "(required for priority change)" : ""}</label>
              <textarea id="update-reason" className="textarea" rows={2} value={updateReason} onChange={(event) => setUpdateReason(event.target.value)} />
            </div>
            <p className="rounded-lg border border-line bg-surface-2 p-2 text-2xs text-muted">
              Every change writes an audit event with actor, reason and request id.
            </p>
          </div>
        ) : null}
      </Modal>
    </div>
  );
}
