import { create } from "zustand";
import { X, AlertTriangle, Inbox, Loader2, CheckCircle2, Info } from "lucide-react";
import clsx from "clsx";
import { useEffect, useState, type ReactNode } from "react";
import type { CoverageLevel, DataState, PriorityLevel, RiskLevel } from "../lib/types";
import { coverageMeta, priorityMeta, riskMeta, stateMeta, statusClass, timeAgo } from "../lib/format";

/* ------------------------------------------------------------------ layout */
export function Card({ children, className, as: Tag = "section" }: { children: ReactNode; className?: string; as?: "section" | "div" | "article" }) {
  return (
    <Tag
      className={clsx(
        "rounded-2xl border border-line/80 bg-surface/90 dark:bg-surface/75 backdrop-blur-xl",
        "shadow-[0_4px_24px_rgba(0,0,0,0.03)] dark:shadow-[0_4px_24px_rgba(0,0,0,0.2)]",
        "transition-all duration-300 relative overflow-hidden",
        className
      )}
    >
      {/* Apple-style top glass reflection line */}
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/40 dark:via-white/10 to-transparent" />
      {children}
    </Tag>
  );
}

export function CardHeader({ title, subtitle, action, icon }: { title: string; subtitle?: string; action?: ReactNode; icon?: ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-3 border-b border-line/70 px-5 py-3.5 bg-surface-2/30">
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          {icon ? <span className="text-forest p-1 rounded-lg bg-forest-soft/60">{icon}</span> : null}
          <h2 className="text-sm font-bold tracking-tight text-ink truncate">{title}</h2>
        </div>
        {subtitle ? <p className="mt-0.5 text-xs text-muted leading-relaxed font-normal">{subtitle}</p> : null}
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}

export function PageHeader({ title, description, actions, meta }: { title: string; description?: string; actions?: ReactNode; meta?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
      <div className="min-w-0 max-w-4xl">
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-ink">{title}</h1>
        {description ? <p className="mt-1.5 text-xs sm:text-sm text-muted leading-relaxed">{description}</p> : null}
        {meta ? <div className="mt-3 flex flex-wrap items-center gap-2.5">{meta}</div> : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2 shrink-0">{actions}</div> : null}
    </div>
  );
}

/* ------------------------------------------------------------------ badges */
export function RiskBadge({ level, index, size = "sm" }: { level?: RiskLevel | null; index?: number | null; size?: "sm" | "lg" }) {
  if (!level) return <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full border border-line text-muted bg-surface-2 text-2xs font-semibold uppercase">NO DATA</span>;
  const meta = riskMeta[level];
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 rounded-full border font-semibold tracking-wide shadow-sm transition-all",
        meta.border, meta.text, meta.bg,
        size === "lg" ? "px-3 py-1 text-xs" : "px-2.5 py-0.5 text-2xs uppercase"
      )}
    >
      <span aria-hidden className="h-1.5 w-1.5 rounded-full animate-pulse" style={{ background: meta.dot }} />
      <span>{meta.label}</span>
      {index !== undefined && index !== null ? (
        <span className="font-mono font-bold opacity-90 pl-0.5">{Math.round(index)}</span>
      ) : null}
    </span>
  );
}

export function PriorityBadge({ level, showLabel = false }: { level?: PriorityLevel | null; showLabel?: boolean }) {
  if (!level) return <span className="inline-flex items-center px-2 py-0.5 rounded-full border border-line text-muted bg-surface-2 text-2xs font-mono">—</span>;
  const tone =
    level === "P1" ? "border-critical/40 text-critical bg-critical/10 shadow-sm"
      : level === "P2" ? "border-warning/40 text-warning bg-warning/10 shadow-sm"
        : level === "P3" ? "border-watch/40 text-watch bg-watch/10 shadow-sm"
          : "border-line text-muted bg-surface-2";
  return (
    <span className={clsx("inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full border text-2xs font-bold font-mono tracking-wider", tone)} title={priorityMeta[level].hint}>
      {level}
      {showLabel ? <span className="font-sans font-medium text-[11px] normal-case opacity-90">({priorityMeta[level].label})</span> : null}
    </span>
  );
}

export function StateBadge({ state, age }: { state?: DataState | null; age?: number | null }) {
  if (!state) return null;
  const meta = stateMeta[state] ?? stateMeta.UNAVAILABLE;
  return (
    <span className={clsx("badge", meta.className)} title={age !== undefined && age !== null ? `Last observation ${timeAgo(new Date(Date.now() - age * 60000).toISOString())}` : undefined}>
      {meta.label}
    </span>
  );
}

export function CoverageBadge({ level }: { level?: CoverageLevel | null }) {
  if (!level) return null;
  const meta = coverageMeta[level];
  return <span className={clsx("badge", meta.className)}>{meta.label}</span>;
}

export function CoverageMeter({ level, coverage }: { level?: CoverageLevel | null; coverage?: { points: number; max_points: number } | null }) {
  if (!level) return null;
  const meta = coverageMeta[level];
  const pct = coverage ? Math.round((coverage.points / coverage.max_points) * 100) : 0;
  return (
    <div>
      <div className="flex items-center justify-between gap-2">
        <span className={clsx("badge", meta.className)}>{meta.label}</span>
        <span className="text-2xs text-muted numeric">{pct}% of cues</span>
      </div>
      <div className="mt-1.5 h-1.5 w-full rounded-full bg-surface-2" role="img" aria-label={`Data coverage ${level}`}>
        <div className={clsx("h-1.5 rounded-full", level === "HIGH" ? "bg-safe" : level === "MEDIUM" ? "bg-watch" : "bg-critical")} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export function StatusBadge({ status }: { status: string }) {
  return <span className={clsx("badge", statusClass(status))}>{status.replaceAll("_", " ")}</span>;
}

export function Chip({ children, tone = "default" }: { children: ReactNode; tone?: "default" | "warn" | "danger" | "ok" }) {
  const toneClass =
    tone === "warn" ? "border-watch/40 text-watch bg-watch/10"
      : tone === "danger" ? "border-critical/40 text-critical bg-critical/10"
        : tone === "ok" ? "border-safe/40 text-safe bg-safe/10"
          : "border-line text-muted bg-surface-2";
  return <span className={clsx("chip", toneClass)}>{children}</span>;
}

/* ------------------------------------------------------------------ feedback */
export function EmptyState({ title, body, action, icon }: { title: string; body?: string; action?: ReactNode; icon?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 px-6 py-12 text-center">
      <div className="rounded-full border border-line bg-surface-2 p-2.5 text-muted">{icon ?? <Inbox size={18} />}</div>
      <h3 className="text-sm font-semibold">{title}</h3>
      {body ? <p className="max-w-md text-xs leading-relaxed text-muted">{body}</p> : null}
      {action}
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const message = error instanceof Error ? error.message : "Something went wrong";
  const isPermission = message.includes("lacks permission") || message.includes("Role 'citizen'");

  return (
    <div className="flex flex-col items-start gap-3 rounded-2xl border border-critical/30 bg-critical/5 p-5 text-sm" role="alert">
      <div className="flex items-center gap-2 font-semibold text-critical">
        <AlertTriangle size={18} />
        {isPermission ? "Authority Clearance Required" : "Could not load this view"}
      </div>
      <p className="text-xs text-muted leading-relaxed">
        {isPermission
          ? "This operational command view is strictly reserved for disaster management officials, geologists, and district magistrates. Citizens should use the Citizen Portal for localized hazard checks and verified shelter routing."
          : message}
      </p>
      <div className="flex flex-wrap items-center gap-2 pt-1">
        {isPermission ? (
          <>
            <a href="/citizen" className="btn btn-sm btn-primary text-xs">
              Open Citizen Portal
            </a>
            <a
              href="/login"
              onClick={() => {
                try {
                  localStorage.removeItem("bhushakti-session");
                } catch (_) {}
              }}
              className="btn btn-sm btn-secondary text-xs"
            >
              Sign in as Administrator (admin@bhushakti.demo)
            </a>
          </>
        ) : (
          onRetry ? <button className="btn btn-sm" onClick={onRetry}>Retry</button> : null
        )}
      </div>
    </div>
  );
}

export function Loading({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 px-4 py-8 text-sm text-muted" role="status">
      <Loader2 size={16} className="animate-spin" /> {label}…
    </div>
  );
}

export function SkeletonRows({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-2 p-4">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="skeleton h-8 w-full" />
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ overlays */
export function Drawer({ open, onClose, title, children, footer, subtitle }: {
  open: boolean; onClose: () => void; title: string; subtitle?: string; children: ReactNode; footer?: ReactNode;
}) {
  useEffect(() => {
    const handler = (event: KeyboardEvent) => { if (event.key === "Escape") onClose(); };
    if (open) document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-[60]">
      <button aria-label="Close panel" className="absolute inset-0 bg-charcoal/40" onClick={onClose} />
      <aside className="drawer-panel" role="dialog" aria-modal="true" aria-label={title}>
        <header className="flex items-start justify-between gap-3 border-b border-line px-4 py-3">
          <div className="min-w-0">
            <h2 className="truncate text-base font-semibold">{title}</h2>
            {subtitle ? <p className="mt-0.5 text-xs text-muted">{subtitle}</p> : null}
          </div>
          <button className="btn btn-ghost btn-sm" onClick={onClose} aria-label="Close"><X size={16} /></button>
        </header>
        <div className="flex-1 overflow-y-auto">{children}</div>
        {footer ? <footer className="border-t border-line bg-surface-2 px-4 py-3">{footer}</footer> : null}
      </aside>
    </div>
  );
}

export function Modal({ open, onClose, title, children, footer, width = "max-w-lg" }: {
  open: boolean; onClose: () => void; title: string; children: ReactNode; footer?: ReactNode; width?: string;
}) {
  useEffect(() => {
    const handler = (event: KeyboardEvent) => { if (event.key === "Escape") onClose(); };
    if (open) document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center p-4">
      <button aria-label="Close dialog" className="absolute inset-0 bg-charcoal/50" onClick={onClose} />
      <div className={clsx("modal-panel relative z-10", width)} role="dialog" aria-modal="true" aria-label={title}>
        <header className="flex items-center justify-between border-b border-line px-4 py-3">
          <h2 className="text-sm font-semibold">{title}</h2>
          <button className="btn btn-ghost btn-sm" onClick={onClose} aria-label="Close"><X size={16} /></button>
        </header>
        <div className="max-h-[70vh] overflow-y-auto px-4 py-3">{children}</div>
        {footer ? <footer className="flex justify-end gap-2 border-t border-line bg-surface-2 px-4 py-3">{footer}</footer> : null}
      </div>
    </div>
  );
}

export function Tabs<T extends string>({ tabs, active, onChange }: { tabs: Array<{ id: T; label: string }>; active: T; onChange: (id: T) => void }) {
  return (
    <div role="tablist" className="flex gap-1 overflow-x-auto border-b border-line px-2">
      {tabs.map((tab) => (
        <button key={tab.id} role="tab" aria-selected={active === tab.id} className="tab" onClick={() => onChange(tab.id)}>
          {tab.label}
        </button>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ toasts */
type Toast = { id: number; message: string; tone: "ok" | "error" | "info" };
const useToasts = create<{ items: Toast[]; push: (message: string, tone: Toast["tone"]) => void; remove: (id: number) => void }>((set, get) => ({
  items: [],
  push: (message, tone) => {
    const id = Date.now() + Math.random();
    set({ items: [...get().items, { id, message, tone }] });
    window.setTimeout(() => get().remove(id), 6000);
  },
  remove: (id) => set({ items: get().items.filter((t) => t.id !== id) }),
}));

export function toast(message: string, tone: "ok" | "error" | "info" = "info") {
  useToasts.getState().push(message, tone);
}

export function Toaster() {
  const items = useToasts((s) => s.items);
  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-[100] flex w-[min(92vw,380px)] flex-col gap-2" aria-live="polite">
      {items.map((item) => (
        <div key={item.id} className={clsx("pointer-events-auto flex items-start gap-2 rounded-lg border bg-surface px-3 py-2 text-sm shadow-panel",
          item.tone === "error" ? "border-critical/40" : item.tone === "ok" ? "border-safe/40" : "border-line")}>
          {item.tone === "error" ? <AlertTriangle size={16} className="mt-0.5 shrink-0 text-critical" />
            : item.tone === "ok" ? <CheckCircle2 size={16} className="mt-0.5 shrink-0 text-safe" />
              : <Info size={16} className="mt-0.5 shrink-0 text-subtle" />}
          <span className="leading-snug">{item.message}</span>
        </div>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ notes */
export function UncalibratedNote({ compact = false }: { compact?: boolean }) {
  if (compact) {
    return <span className="chip border-watch/40 text-watch">Uncalibrated index — not a probability</span>;
  }
  return (
    <p className="prose-note">
      <strong className="text-ink">Hazard is a 0–100 prototype index, not a probability.</strong>{" "}
      It is not calibrated to observed landslide frequency and must not be read as “chance of a landslide”.
    </p>
  );
}

export function ReasonDialog({
  open, title, description, confirmLabel, minLength = 4, busy = false, onClose, onConfirm,
}: {
  open: boolean;
  title: string;
  description?: string;
  confirmLabel: string;
  minLength?: number;
  busy?: boolean;
  onClose: () => void;
  onConfirm: (reason: string) => void;
}) {
  const [reason, setReason] = useState("");
  useEffect(() => { setReason(""); }, [open]);
  const valid = reason.trim().length >= minLength;
  return (
    <Modal
      open={open}
      onClose={onClose}
      title={title}
      footer={
        <>
          <button className="btn btn-sm" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary btn-sm" disabled={!valid || busy} onClick={() => onConfirm(reason.trim())}>
            {busy ? "Saving…" : confirmLabel}
          </button>
        </>
      }
    >
      <div className="space-y-3 text-sm">
        {description ? <p className="text-xs leading-relaxed text-muted">{description}</p> : null}
        <div>
          <label className="label" htmlFor="reason-dialog-text">Reason (recorded in the audit trail)</label>
          <textarea
            id="reason-dialog-text"
            className="textarea"
            rows={3}
            autoFocus
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            placeholder={`At least ${minLength} characters`}
          />
          <p className="hint mt-1 numeric">{reason.trim().length} / {minLength} characters minimum</p>
        </div>
      </div>
    </Modal>
  );
}

export function FieldNote({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <div>
      <div className="kpi-label">{label}</div>
      <div className="mt-0.5 text-sm font-medium">{value}</div>
      {hint ? <div className="hint mt-0.5">{hint}</div> : null}
    </div>
  );
}
