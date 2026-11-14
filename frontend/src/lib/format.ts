import type { CoverageLevel, DataState, PriorityLevel, RiskLevel } from "./types";

const dateTime = new Intl.DateTimeFormat("en-IN", {
  timeZone: "Asia/Kolkata",
  day: "2-digit",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

const dateOnly = new Intl.DateTimeFormat("en-IN", {
  timeZone: "Asia/Kolkata",
  day: "2-digit",
  month: "short",
  year: "numeric",
});

export function fmtDateTime(value?: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return `${dateTime.format(date)} IST`;
}

export function fmtDate(value?: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : dateOnly.format(date);
}

export function timeAgo(value?: string | null): string {
  if (!value) return "never";
  const date = new Date(value).getTime();
  if (Number.isNaN(date)) return "unknown";
  const minutes = Math.max(0, Math.round((Date.now() - date) / 60000));
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  const days = Math.round(hours / 24);
  return `${days} d ago`;
}

export function fmtNumber(value?: number | null, digits = 0): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return value.toLocaleString("en-IN", { maximumFractionDigits: digits, minimumFractionDigits: digits });
}

export function fmtCompact(value?: number | null): string {
  if (value === null || value === undefined) return "—";
  return new Intl.NumberFormat("en-IN", { notation: "compact", maximumFractionDigits: 1 }).format(value);
}

export const riskMeta: Record<RiskLevel, { label: string; text: string; bg: string; border: string; dot: string; fill: string }> = {
  SAFE: { label: "Safe", text: "text-safe", bg: "bg-safe/10", border: "border-safe/40", dot: "#2f7d4f", fill: "rgba(47,125,79,0.35)" },
  WATCH: { label: "Watch", text: "text-watch", bg: "bg-watch/10", border: "border-watch/40", dot: "#a16207", fill: "rgba(161,98,7,0.38)" },
  WARNING: { label: "Warning", text: "text-warning", bg: "bg-warning/10", border: "border-warning/40", dot: "#c2410c", fill: "rgba(194,65,12,0.42)" },
  CRITICAL: { label: "Critical", text: "text-critical", bg: "bg-critical/10", border: "border-critical/50", dot: "#b91c1c", fill: "rgba(185,28,28,0.48)" },
};

export const priorityMeta: Record<PriorityLevel, { label: string; hint: string }> = {
  P1: { label: "IMMEDIATE", hint: "Act now" },
  P2: { label: "URGENT", hint: "Within 24 h" },
  P3: { label: "MONITOR", hint: "This week" },
  P4: { label: "ROUTINE", hint: "Next cycle" },
};

export const stateMeta: Record<DataState, { label: string; className: string }> = {
  LIVE: { label: "LIVE", className: "border-safe/40 text-safe bg-safe/10" },
  CACHED: { label: "CACHED", className: "border-subtle/40 text-subtle bg-subtle/10" },
  STALE: { label: "STALE", className: "border-watch/40 text-watch bg-watch/10" },
  DEGRADED: { label: "DEGRADED", className: "border-warning/40 text-warning bg-warning/10" },
  UNAVAILABLE: { label: "UNAVAILABLE", className: "border-line text-muted bg-surface-2" },
  SIMULATED: { label: "SIMULATED", className: "border-critical/40 text-critical bg-critical/10" },
};

export const coverageMeta: Record<CoverageLevel, { label: string; className: string }> = {
  HIGH: { label: "DATA COVERAGE: HIGH", className: "border-safe/40 text-safe bg-safe/10" },
  MEDIUM: { label: "DATA COVERAGE: MEDIUM", className: "border-watch/40 text-watch bg-watch/10" },
  LOW: { label: "DATA COVERAGE: LOW", className: "border-critical/40 text-critical bg-critical/10" },
};

export function titleCase(value?: string | null): string {
  if (!value) return "—";
  return value
    .toLowerCase()
    .split(/[_\s-]+/)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function statusClass(status: string): string {
  switch (status) {
    case "DELIVERED":
    case "APPROVED":
    case "VERIFIED":
    case "RESOLVED":
    case "OPEN":
      return "border-safe/40 text-safe bg-safe/10";
    case "CANDIDATE":
    case "PENDING_VERIFICATION":
    case "REVIEWED":
    case "AT_RISK":
    case "RESTRICTED":
      return "border-watch/40 text-watch bg-watch/10";
    case "REJECTED":
    case "BLOCKED":
    case "CANCELLED":
      return "border-critical/40 text-critical bg-critical/10";
    case "EXPIRED":
    case "ALL_CLEAR":
      return "border-line text-muted bg-surface-2";
    default:
      return "border-subtle/40 text-subtle bg-subtle/10";
  }
}
