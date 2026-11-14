import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Activity, KeyRound, ScrollText, ShieldCheck, SlidersHorizontal, UserPlus, Users } from "lucide-react";
import clsx from "clsx";
import { api, qs } from "../lib/api";
import { fmtDateTime, timeAgo, titleCase } from "../lib/format";
import { useSession } from "../store/session";
import { Card, EmptyState, ErrorState, Loading, Modal, StatusBadge, Tabs, toast } from "../components/ui";

type Tab = "users" | "flags" | "policy" | "audit" | "health";

interface UserRow {
  id: number; email: string; name: string; role: string; role_label: string;
  districts: string[]; is_active: boolean; last_login_at: string | null; created_at: string;
}
interface UsersPayload {
  users: UserRow[];
  roles: Array<{ role: string; label: string }>;
  districts: Array<{ code: string; name: string; state: string }>;
}
interface FlagsPayload { flags: Array<{ key: string; enabled: boolean; description: string; updated_by: string | null; updated_at: string }> }
interface PolicyPayload {
  policies: Array<{ version: string; name: string; thresholds: Record<string, number>; hysteresis_points: number; min_duration_min: number; dedupe_window_min: number; active: boolean; created_at: string }>;
  approval_required: boolean;
  note: string;
}
interface AuditPayload {
  entries: Array<{ id: number; at: string; actor: string; role: string; action: string; entity: string; entity_id: string; reason: string; payload: Record<string, unknown>; request_id: string; ip: string }>;
  meta: { total: number; limit: number; offset: number };
}
interface HealthPayload {
  status: string; environment: string; demo_mode: boolean; ingestion_enabled: boolean; weather_mode: string;
  model_version: string; counts: Record<string, number>;
  sources: Array<{ id: string; state: string; last_success_at: string | null; last_error: string | null }>;
  sse_subscribers: number; checked_at: string;
}

export default function Admin() {
  const me = useSession((s) => s.user);
  const has = useSession((s) => s.has);
  const [tab, setTab] = useState<Tab>("users");
  const [createOpen, setCreateOpen] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", role: "field_officer", password: "", districts: [] as string[] });
  const [policyForm, setPolicyForm] = useState({ name: "Prototype policy revision", watch: 40, warning: 60, critical: 80, hysteresis_points: 5, min_duration_min: 30, dedupe_window_min: 180 });
  const [auditFilter, setAuditFilter] = useState("");
  const queryClient = useQueryClient();

  const users = useQuery({ queryKey: ["admin-users"], queryFn: () => api<UsersPayload>("/api/v1/admin/users"), enabled: tab === "users" && has("users:read") });
  const flags = useQuery({ queryKey: ["flags"], queryFn: () => api<FlagsPayload>("/api/v1/admin/feature-flags"), enabled: tab === "flags" && has("admin:read") });
  const policy = useQuery({ queryKey: ["policy"], queryFn: () => api<PolicyPayload>("/api/v1/admin/alert-policy"), enabled: tab === "policy" });
  const audit = useQuery({
    queryKey: ["audit", auditFilter],
    queryFn: () => api<AuditPayload>(`/api/v1/admin/audit-logs${qs({ action: auditFilter || undefined, limit: 200 })}`),
    enabled: tab === "audit" && has("audit:read"),
  });
  const health = useQuery({ queryKey: ["health"], queryFn: () => api<HealthPayload>("/api/v1/admin/system-health"), enabled: tab === "health", refetchInterval: 60_000 });

  const invalidate = () => queryClient.invalidateQueries();
  const createUser = useMutation({
    mutationFn: () => api("/api/v1/admin/users", { method: "POST", json: form }),
    onSuccess: () => { toast("User provisioned", "ok"); setCreateOpen(false); setForm({ name: "", email: "", role: "field_officer", password: "", districts: [] }); invalidate(); },
    onError: (error) => toast(error instanceof Error ? error.message : "Could not create user", "error"),
  });
  const setActive = useMutation({
    mutationFn: ({ id, is_active }: { id: number; is_active: boolean }) => api(`/api/v1/admin/users/${id}`, { method: "PATCH", json: { is_active, reason: "Administrative change" } }),
    onSuccess: () => { toast("User updated", "ok"); invalidate(); },
    onError: (error) => toast(error instanceof Error ? error.message : "Update failed", "error"),
  });
  const toggleFlag = useMutation({
    mutationFn: ({ key, enabled }: { key: string; enabled: boolean }) => api(`/api/v1/admin/feature-flags/${key}`, { method: "PATCH", json: { enabled } }),
    onSuccess: () => { toast("Feature flag updated and audited", "ok"); invalidate(); },
    onError: (error) => toast(error instanceof Error ? error.message : "Flag change refused", "error"),
  });
  const createPolicy = useMutation({
    mutationFn: () => api("/api/v1/admin/alert-policy", { method: "POST", json: { ...policyForm, activate: true } }),
    onSuccess: () => { toast("New policy version activated", "ok"); invalidate(); },
    onError: (error) => toast(error instanceof Error ? error.message : "Policy rejected", "error"),
  });

  const groupedAudit = useMemo(() => audit.data?.entries ?? [], [audit.data]);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Administration</h1>
        <p className="text-sm text-muted">Users, policy, feature flags and the append-only audit trail.</p>
      </div>

      <Card>
        <Tabs
          tabs={[
            { id: "users", label: "Users & roles" },
            { id: "flags", label: "Feature flags" },
            { id: "policy", label: "Alert policy" },
            { id: "audit", label: "Audit trail" },
            { id: "health", label: "System health" },
          ]}
          active={tab}
          onChange={setTab}
        />

        {tab === "users" ? (
          <div className="p-3">
            <div className="mb-2 flex items-center justify-between">
              <p className="text-xs text-muted">District scoping restricts every query and mutation server-side.</p>
              {has("users:write") ? <button className="btn btn-sm" onClick={() => setCreateOpen(true)}><UserPlus size={14} /> Provision user</button> : null}
            </div>
            {users.isLoading ? <Loading /> : null}
            {users.error ? <ErrorState error={users.error} onRetry={() => users.refetch()} /> : null}
            <div className="table-wrap">
              <table className="data">
                <thead><tr><th>Name</th><th>Role</th><th>Districts</th><th>Status</th><th>Last login</th><th /></tr></thead>
                <tbody>
                  {(users.data?.users ?? []).map((user) => (
                    <tr key={user.id}>
                      <td><div className="font-medium">{user.name}{user.id === me?.id ? <span className="ml-1 text-2xs text-muted">(you)</span> : null}</div><div className="text-2xs text-muted">{user.email}</div></td>
                      <td className="text-xs">{user.role_label}</td>
                      <td className="text-2xs text-muted">{user.districts.length ? user.districts.join(", ") : "Statewide"}</td>
                      <td><span className={clsx("badge", user.is_active ? "border-safe/40 text-safe bg-safe/10" : "border-line text-muted bg-surface-2")}>{user.is_active ? "ACTIVE" : "DISABLED"}</span></td>
                      <td className="text-2xs text-muted">{user.last_login_at ? timeAgo(user.last_login_at) : "never"}</td>
                      <td>
                        {has("users:write") && user.id !== me?.id ? (
                          <button className="btn btn-sm" onClick={() => setActive.mutate({ id: user.id, is_active: !user.is_active })}>
                            {user.is_active ? "Disable" : "Enable"}
                          </button>
                        ) : null}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {!users.isLoading && !(users.data?.users ?? []).length ? <EmptyState icon={<Users size={18} />} title="No users visible" body="Your role may not include users:read." /> : null}
          </div>
        ) : null}

        {tab === "flags" ? (
          <div className="p-3">
            <p className="mb-2 text-xs text-muted">Flags gate delivery and AI features. They cannot override safety rules such as human approval.</p>
            {flags.isLoading ? <Loading /> : null}
            {flags.error ? <ErrorState error={flags.error} onRetry={() => flags.refetch()} /> : null}
            <div className="space-y-2">
              {(flags.data?.flags ?? []).map((flag) => (
                <div key={flag.key} className="flex flex-wrap items-start justify-between gap-2 rounded-lg border border-line px-3 py-2">
                  <div className="min-w-0">
                    <div className="mono text-xs font-semibold">{flag.key}</div>
                    <div className="text-2xs text-muted">{flag.description}</div>
                    <div className="text-2xs text-muted">Updated {timeAgo(flag.updated_at)} {flag.updated_by ? `by ${flag.updated_by}` : ""}</div>
                  </div>
                  <button
                    className={clsx("btn btn-sm", flag.enabled && "border-forest text-forest")}
                    disabled={!has("flags:write") || toggleFlag.isPending}
                    aria-pressed={flag.enabled}
                    onClick={() => toggleFlag.mutate({ key: flag.key, enabled: !flag.enabled })}
                  >
                    {flag.enabled ? "ENABLED" : "DISABLED"}
                  </button>
                </div>
              ))}
            </div>
            <p className="mt-2 text-2xs text-muted">
              Enabling SMS or email does not create a provider. Delivery attempts are recorded as BLOCKED with the
              missing-provider reason rather than being reported as sent.
            </p>
          </div>
        ) : null}

        {tab === "policy" ? (
          <div className="grid gap-3 p-3 lg:grid-cols-2">
            <div>
              <h3 className="section-title mb-2 flex items-center gap-1.5"><ShieldCheck size={15} /> Versions</h3>
              {policy.isLoading ? <Loading /> : null}
              {policy.error ? <ErrorState error={policy.error} onRetry={() => policy.refetch()} /> : null}
              <div className="space-y-2">
                {(policy.data?.policies ?? []).map((item) => (
                  <div key={item.version} className="rounded-lg border border-line px-3 py-2">
                    <div className="flex items-center justify-between gap-2">
                      <span className="mono text-xs">{item.version}</span>
                      <span className={clsx("badge", item.active ? "border-safe/40 text-safe bg-safe/10" : "border-line text-muted bg-surface-2")}>{item.active ? "ACTIVE" : "RETIRED"}</span>
                    </div>
                    <div className="mt-1 text-xs">{item.name}</div>
                    <div className="mt-1 flex flex-wrap gap-1 text-2xs text-muted">
                      {Object.entries(item.thresholds).map(([level, value]) => <span key={level} className="chip">{level} ≥ {value}</span>)}
                      <span className="chip">hysteresis {item.hysteresis_points}</span>
                      <span className="chip">min {item.min_duration_min} min</span>
                      <span className="chip">dedupe {item.dedupe_window_min} min</span>
                    </div>
                  </div>
                ))}
              </div>
              <p className="mt-2 text-2xs text-muted">{policy.data?.note} Approval required: {policy.data?.approval_required ? "yes" : "no"}.</p>
            </div>
            <div>
              <h3 className="section-title mb-2 flex items-center gap-1.5"><SlidersHorizontal size={15} /> New version</h3>
              {has("flags:write") ? (
                <div className="space-y-2">
                  <div><label className="label" htmlFor="policy-name">Name</label><input id="policy-name" className="input" value={policyForm.name} onChange={(event) => setPolicyForm({ ...policyForm, name: event.target.value })} /></div>
                  <div className="grid grid-cols-3 gap-2">
                    {(["watch", "warning", "critical"] as const).map((key) => (
                      <div key={key}>
                        <label className="label" htmlFor={`policy-${key}`}>{key}</label>
                        <input id={`policy-${key}`} type="number" min={0} max={100} className="input" value={policyForm[key]} onChange={(event) => setPolicyForm({ ...policyForm, [key]: Number(event.target.value) })} />
                      </div>
                    ))}
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    <div><label className="label" htmlFor="p-hyst">Hysteresis</label><input id="p-hyst" type="number" className="input" value={policyForm.hysteresis_points} onChange={(event) => setPolicyForm({ ...policyForm, hysteresis_points: Number(event.target.value) })} /></div>
                    <div><label className="label" htmlFor="p-dur">Min duration</label><input id="p-dur" type="number" className="input" value={policyForm.min_duration_min} onChange={(event) => setPolicyForm({ ...policyForm, min_duration_min: Number(event.target.value) })} /></div>
                    <div><label className="label" htmlFor="p-dedupe">Dedupe</label><input id="p-dedupe" type="number" className="input" value={policyForm.dedupe_window_min} onChange={(event) => setPolicyForm({ ...policyForm, dedupe_window_min: Number(event.target.value) })} /></div>
                  </div>
                  <button className="btn btn-primary btn-sm" disabled={createPolicy.isPending} onClick={() => createPolicy.mutate()}>Activate new policy</button>
                  <p className="hint">Activating retires the previous version; existing approvals remain in the audit trail.</p>
                </div>
              ) : <EmptyState icon={<KeyRound size={18} />} title="Policy changes need platform administration" body="Your role can read thresholds but not activate a new policy version." />}
            </div>
          </div>
        ) : null}

        {tab === "audit" ? (
          <div className="p-3">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <input className="input max-w-xs" placeholder="Filter by action (e.g. alert.approved)" value={auditFilter} onChange={(event) => setAuditFilter(event.target.value)} aria-label="Filter audit actions" />
              <span className="text-2xs text-muted">{audit.data?.meta.total ?? 0} entries</span>
            </div>
            {audit.isLoading ? <Loading /> : null}
            {audit.error ? <ErrorState error={audit.error} onRetry={() => audit.refetch()} /> : null}
            <div className="table-wrap max-h-[560px] overflow-y-auto">
              <table className="data">
                <thead><tr><th>When</th><th>Actor</th><th>Action</th><th>Entity</th><th>Reason</th><th>Request</th></tr></thead>
                <tbody>
                  {groupedAudit.map((entry) => (
                    <tr key={entry.id}>
                      <td className="whitespace-nowrap text-2xs text-muted">{fmtDateTime(entry.at)}</td>
                      <td className="text-2xs"><div>{entry.actor}</div><div className="text-muted">{entry.role}</div></td>
                      <td className="mono text-2xs">{entry.action}</td>
                      <td className="text-2xs text-muted">{entry.entity} #{entry.entity_id}</td>
                      <td className="max-w-[320px] text-2xs text-muted">{entry.reason || "—"}{Object.keys(entry.payload ?? {}).length ? <details className="mt-0.5"><summary className="cursor-pointer">payload</summary><pre className="mt-1 max-w-[300px] overflow-x-auto text-2xs">{JSON.stringify(entry.payload, null, 1)}</pre></details> : null}</td>
                      <td className="mono text-2xs text-muted">{entry.request_id.slice(0, 8)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {!groupedAudit.length && !audit.isLoading ? <EmptyState icon={<ScrollText size={18} />} title="No audit entries" /> : null}
          </div>
        ) : null}

        {tab === "health" ? (
          <div className="p-3">
            {health.isLoading ? <Loading /> : null}
            {health.error ? <ErrorState error={health.error} onRetry={() => health.refetch()} /> : null}
            {health.data ? (
              <div className="space-y-3">
                <div className="grid gap-2 sm:grid-cols-3 lg:grid-cols-6">
                  {Object.entries(health.data.counts).map(([key, value]) => (
                    <div key={key} className="rounded-lg border border-line bg-canvas px-3 py-2">
                      <div className="kpi-label">{titleCase(key)}</div>
                      <div className="stat-value">{value}</div>
                    </div>
                  ))}
                </div>
                <div className="grid gap-2 text-xs sm:grid-cols-2">
                  <div className="rounded-lg border border-line px-3 py-2">
                    <div className="kpi-label">Runtime</div>
                    Environment {health.data.environment} · weather mode {health.data.weather_mode} · demo {String(health.data.demo_mode)} ·
                    ingestion {health.data.ingestion_enabled ? "enabled" : "disabled"} · model {health.data.model_version}
                  </div>
                  <div className="rounded-lg border border-line px-3 py-2">
                    <div className="kpi-label">Live stream</div>
                    {health.data.sse_subscribers} SSE subscriber(s) · checked {timeAgo(health.data.checked_at)}
                  </div>
                </div>
                <div className="rounded-lg border border-line">
                  <div className="border-b border-line px-3 py-2 text-xs font-semibold flex items-center gap-1.5"><Activity size={14} /> Source states</div>
                  <div className="divide-y divide-line">
                    {health.data.sources.map((source) => (
                      <div key={source.id} className="flex items-center justify-between gap-2 px-3 py-1.5 text-2xs">
                        <span className="mono">{source.id}</span>
                        <div className="flex items-center gap-2">
                          <span className="text-muted">{source.last_success_at ? timeAgo(source.last_success_at) : "never"}</span>
                          <StatusBadge status={source.state} />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        ) : null}
      </Card>

      <Modal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        title="Provision user"
        footer={
          <>
            <button className="btn btn-sm" onClick={() => setCreateOpen(false)}>Cancel</button>
            <button
              className="btn btn-primary btn-sm"
              disabled={form.name.length < 2 || !form.email.includes("@") || form.password.length < 12 || createUser.isPending}
              onClick={() => createUser.mutate()}
            >
              Create
            </button>
          </>
        }
      >
        <div className="space-y-2">
          <div className="grid gap-2 sm:grid-cols-2">
            <div><label className="label" htmlFor="u-name">Name</label><input id="u-name" className="input" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></div>
            <div><label className="label" htmlFor="u-email">Email</label><input id="u-email" type="email" className="input" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} /></div>
          </div>
          <div><label className="label" htmlFor="u-role">Role</label>
            <select id="u-role" className="select" value={form.role} onChange={(event) => setForm({ ...form, role: event.target.value })}>
              {(users.data?.roles ?? []).map((role) => <option key={role.role} value={role.role}>{role.label}</option>)}
            </select>
          </div>
          <div><label className="label" htmlFor="u-password">Temporary password (min 12 chars)</label><input id="u-password" type="password" className="input" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} /></div>
          <div>
            <span className="label">District scope</span>
            <div className="flex flex-wrap gap-2">
              {(users.data?.districts ?? []).map((district) => (
                <label key={district.code} className="flex items-center gap-1 rounded border border-line px-2 py-1 text-xs">
                  <input
                    type="checkbox"
                    checked={form.districts.includes(district.code)}
                    onChange={(event) => setForm({ ...form, districts: event.target.checked ? [...form.districts, district.code] : form.districts.filter((code) => code !== district.code) })}
                  />
                  {district.name}
                </label>
              ))}
            </div>
            <p className="hint">No districts means statewide scope for state/platform roles.</p>
          </div>
        </div>
      </Modal>
    </div>
  );
}
