import React, { useState, useRef, type ReactNode } from "react";
import clsx from "clsx";
import { CheckCircle2, Star, ShieldCheck } from "lucide-react";

/* ------------------------------------------------------------------ Background Grid / Dot Mesh */
export function DotBackground({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={clsx(
        "relative w-full overflow-hidden bg-canvas",
        "bg-dot-pattern",
        className
      )}
    >
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-transparent via-canvas/40 to-canvas" />
      <div className="relative z-10">{children}</div>
    </div>
  );
}

/* ------------------------------------------------------------------ Bento Grid */
export function BentoGrid({
  className,
  children,
}: {
  className?: string;
  children?: ReactNode;
}) {
  return (
    <div
      className={clsx(
        "grid md:auto-rows-[18rem] grid-cols-1 md:grid-cols-3 gap-4 max-w-7xl mx-auto",
        className
      )}
    >
      {children}
    </div>
  );
}

export function BentoGridItem({
  className,
  title,
  description,
  header,
  icon,
  badge,
  onClick,
}: {
  className?: string;
  title?: string | ReactNode;
  description?: string | ReactNode;
  header?: ReactNode;
  icon?: ReactNode;
  badge?: ReactNode;
  onClick?: () => void;
}) {
  return (
    <div
      onClick={onClick}
      className={clsx(
        "row-span-1 rounded-2xl group/bento hover:shadow-2xl transition duration-300",
        "p-5 bg-surface/90 dark:bg-surface/80 backdrop-blur-xl border border-line",
        "hover:border-forest/40 dark:hover:border-forest/50",
        "justify-between flex flex-col space-y-4 relative overflow-hidden",
        onClick && "cursor-pointer",
        className
      )}
    >
      {/* Ambient glass reflection */}
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/30 dark:via-white/10 to-transparent" />
      
      {header && <div className="w-full flex-1 min-h-[6rem]">{header}</div>}
      
      <div className="group-hover/bento:translate-x-1 transition duration-200">
        <div className="flex items-center justify-between mb-2">
          {icon && <div className="text-forest p-2 rounded-xl bg-forest-soft w-fit">{icon}</div>}
          {badge && <div>{badge}</div>}
        </div>
        <div className="font-bold text-ink text-base tracking-tight mb-1">
          {title}
        </div>
        <div className="font-normal text-muted text-xs leading-relaxed">
          {description}
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ Spotlight Card (Apple / Aceternity) */
export function SpotlightCard({
  children,
  className,
  onClick,
}: {
  children: ReactNode;
  className?: string;
  onClick?: () => void;
}) {
  const divRef = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [opacity, setOpacity] = useState(0);

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!divRef.current) return;
    const rect = divRef.current.getBoundingClientRect();
    setPosition({ x: e.clientX - rect.left, y: e.clientY - rect.top });
  };

  const handleMouseEnter = () => setOpacity(1);
  const handleMouseLeave = () => setOpacity(0);

  return (
    <div
      ref={divRef}
      onMouseMove={handleMouseMove}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onClick={onClick}
      className={clsx(
        "relative rounded-2xl border border-line bg-surface/90 dark:bg-surface/75 backdrop-blur-xl p-5",
        "overflow-hidden transition-all duration-300 hover:shadow-xl",
        onClick && "cursor-pointer",
        className
      )}
    >
      {/* Spotlight Radial Glow */}
      <div
        className="pointer-events-none absolute -inset-px transition duration-300"
        style={{
          opacity,
          background: `radial-gradient(400px circle at ${position.x}px ${position.y}px, rgba(34, 197, 94, 0.12), transparent 80%)`,
        }}
      />
      {/* Top subtle highlight line */}
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/40 dark:via-white/15 to-transparent" />
      <div className="relative z-10">{children}</div>
    </div>
  );
}

/* ------------------------------------------------------------------ Glowing Moving Border Card */
export function GlowingCard({
  children,
  className,
  glowColor = "from-emerald-500 via-teal-500 to-emerald-600",
}: {
  children: ReactNode;
  className?: string;
  glowColor?: string;
}) {
  return (
    <div className={clsx("relative p-[1.5px] rounded-2xl overflow-hidden group", className)}>
      <div
        className={clsx(
          "absolute inset-0 bg-gradient-to-r animate-spin-slow opacity-75 blur-sm group-hover:opacity-100 transition duration-500",
          glowColor
        )}
      />
      <div className="relative bg-surface dark:bg-[#121614] rounded-2xl p-5 backdrop-blur-xl border border-line/40 h-full">
        {children}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ Shimmer Button (Apple Keynote Style) */
export function ShimmerButton({
  children,
  onClick,
  className,
  disabled,
  variant = "primary",
}: {
  children: ReactNode;
  onClick?: () => void;
  className?: string;
  disabled?: boolean;
  variant?: "primary" | "secondary";
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={clsx(
        "relative inline-flex items-center justify-center px-4 py-2 text-xs font-semibold rounded-xl",
        "overflow-hidden transition-all duration-300 active:scale-[0.98] disabled:opacity-50",
        variant === "primary"
          ? "bg-forest text-white shadow-lg shadow-forest/20 hover:shadow-forest/35 hover:brightness-105"
          : "bg-surface-2 text-ink border border-line hover:bg-surface",
        className
      )}
    >
      {/* Shimmer sweep effect */}
      <span className="absolute top-0 -left-[100%] w-full h-full bg-gradient-to-r from-transparent via-white/20 to-transparent -skew-x-12 animate-shimmer" />
      <span className="relative z-10 flex items-center gap-1.5">{children}</span>
    </button>
  );
}

/* ------------------------------------------------------------------ Segmented Control (Apple iOS/macOS) */
export function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
  className,
}: {
  options: Array<{ value: T; label: string; icon?: ReactNode }>;
  value: T;
  onChange: (val: T) => void;
  className?: string;
}) {
  return (
    <div
      className={clsx(
        "inline-flex p-1 bg-surface-2/80 dark:bg-surface-2/60 backdrop-blur-md rounded-xl border border-line",
        className
      )}
    >
      {options.map((opt) => {
        const isSelected = opt.value === value;
        return (
          <button
            key={opt.value}
            onClick={() => onChange(opt.value)}
            className={clsx(
              "px-3 py-1.5 text-xs font-medium rounded-lg transition-all duration-200 flex items-center gap-1.5",
              isSelected
                ? "bg-surface dark:bg-surface text-ink font-semibold shadow-sm border border-line/60"
                : "text-muted hover:text-ink"
            )}
          >
            {opt.icon}
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}

/* ------------------------------------------------------------------ NerdWallet Trust / Rating Badge */
export function ReliabilityBadge({
  score,
  label = "BhuShakti Safety Index",
  verified = true,
}: {
  score: number | string;
  label?: string;
  verified?: boolean;
}) {
  return (
    <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-surface border border-line shadow-sm">
      <div className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-bold text-xs">
        <Star size={13} className="fill-current text-emerald-500" />
        <span className="tabular-nums font-mono">{score}</span>
        <span className="text-[10px] text-muted font-normal">/100</span>
      </div>
      <div className="h-3 w-px bg-line" />
      <span className="text-xs font-medium text-ink">{label}</span>
      {verified && (
        <span className="flex items-center text-emerald-600 dark:text-emerald-400" title="Authority Verified Methodology">
          <CheckCircle2 size={13} />
        </span>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ NerdWallet Editorial Disclosure Pill */
export function DisclosurePill({
  text = "Verified Methodology: GSI + Copernicus DEM + Open-Meteo Telemetry",
  tooltip,
}: {
  text?: string;
  tooltip?: string;
}) {
  return (
    <div
      title={tooltip}
      className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-surface-2/70 border border-line text-[11px] text-muted cursor-help"
    >
      <ShieldCheck size={12} className="text-forest shrink-0" />
      <span>{text}</span>
    </div>
  );
}

/* ------------------------------------------------------------------ Apple Glass Stat Card */
export function AppleGlassStat({
  label,
  value,
  caption,
  trend,
  trendTone = "neutral",
  icon,
  delta,
  deltaType,
}: {
  label: string;
  value: ReactNode;
  caption?: string;
  trend?: string;
  trendTone?: "positive" | "negative" | "warning" | "neutral";
  icon?: ReactNode;
  delta?: string;
  deltaType?: "positive" | "negative" | "warning" | "neutral" | string;
}) {
  const effectiveCaption = caption || delta;
  const effectiveTrend = trend;
  const effectiveTone = (trendTone || deltaType || "neutral") as "positive" | "negative" | "warning" | "neutral";

  return (
    <div className="relative rounded-2xl bg-surface/90 dark:bg-surface/70 backdrop-blur-xl border border-line p-4 shadow-sm hover:shadow-md transition-all">
      <div className="flex items-center justify-between text-muted mb-2">
        <span className="text-2xs uppercase tracking-wider font-semibold">{label}</span>
        {icon && <span className="p-1.5 rounded-lg bg-surface-2 text-ink">{icon}</span>}
      </div>
      <div className="text-2xl font-bold tracking-tight text-ink tabular-nums">{value}</div>
      {(effectiveCaption || effectiveTrend) && (
        <div className="mt-1 flex items-center gap-2 text-xs">
          {effectiveTrend && (
            <span
              className={clsx(
                "font-semibold text-2xs px-1.5 py-0.5 rounded",
                effectiveTone === "positive" && "text-emerald-600 bg-emerald-500/10",
                effectiveTone === "negative" && "text-rose-600 bg-rose-500/10",
                effectiveTone === "warning" && "text-amber-600 bg-amber-500/10",
                effectiveTone === "neutral" && "text-muted bg-surface-2"
              )}
            >
              {effectiveTrend}
            </span>
          )}
          {effectiveCaption && (
            <span
              className={clsx(
                "text-[11px]",
                effectiveTone === "positive" ? "text-emerald-600 dark:text-emerald-400 font-medium" :
                effectiveTone === "negative" ? "text-rose-600 dark:text-rose-400 font-medium" :
                effectiveTone === "warning" ? "text-amber-600 dark:text-amber-400 font-medium" :
                "text-muted"
              )}
            >
              {effectiveCaption}
            </span>
          )}
        </div>
      )}
    </div>
  );
}


/* ------------------------------------------------------------------ Hover Border Gradient (Aceternity) */
export function HoverBorderGradient({
  children,
  className,
  as: Tag = "button",
  containerClassName,
  onClick,
  active = false,
}: {
  children: ReactNode;
  className?: string;
  as?: any;
  containerClassName?: string;
  onClick?: () => void;
  active?: boolean;
}) {
  const [hovered, setHovered] = useState(false);

  return (
    <Tag
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      className={clsx(
        "relative p-[1.5px] rounded-2xl overflow-hidden transition-all duration-300 w-fit inline-block",
        containerClassName
      )}
    >
      <div
        className={clsx(
          "absolute inset-0 bg-gradient-to-r transition-opacity duration-500",
          hovered || active
            ? "from-emerald-500 via-teal-400 to-emerald-600 opacity-100 animate-spin-slow"
            : "from-transparent via-line to-transparent opacity-40"
        )}
      />
      <div
        className={clsx(
          "relative z-10 rounded-[14px] bg-surface dark:bg-[#151a17] px-4 py-2 text-ink text-xs font-semibold backdrop-blur-xl transition duration-200",
          className
        )}
      >
        {children}
      </div>
    </Tag>
  );
}

/* ------------------------------------------------------------------ Infinite Moving Ticker / Cards */
export function InfiniteMovingCards({
  items,
  className,
}: {
  items: Array<{
    title: string;
    subtitle: string;
    badge?: string;
    badgeVariant?: "safe" | "warning" | "critical" | "neutral";
    icon?: ReactNode;
  }>;
  className?: string;
}) {
  return (
    <div className={clsx("w-full overflow-hidden [mask-image:linear-gradient(to_right,transparent,white_10%,white_90%,transparent)]", className)}>
      <div className="animate-marquee py-2 gap-3 flex">
        {[...items, ...items].map((item, idx) => (
          <div
            key={idx}
            className="flex items-center gap-3 px-3.5 py-2 rounded-xl bg-surface/85 dark:bg-surface/60 backdrop-blur-md border border-line shrink-0 shadow-sm hover:border-forest/40 transition-colors"
          >
            {item.icon && <span className="text-forest p-1 rounded-lg bg-forest-soft shrink-0">{item.icon}</span>}
            <div className="text-left">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-ink whitespace-nowrap">{item.title}</span>
                {item.badge && (
                  <span
                    className={clsx(
                      "text-[9px] font-mono font-bold px-1.5 py-0.5 rounded-full uppercase",
                      item.badgeVariant === "critical" && "bg-critical/15 text-critical border border-critical/30",
                      item.badgeVariant === "warning" && "bg-warning/15 text-warning border border-warning/30",
                      item.badgeVariant === "safe" && "bg-safe/15 text-safe border border-safe/30",
                      (!item.badgeVariant || item.badgeVariant === "neutral") && "bg-surface-2 text-muted border border-line"
                    )}
                  >
                    {item.badge}
                  </span>
                )}
              </div>
              <span className="text-[10px] text-muted whitespace-nowrap block mt-0.5">{item.subtitle}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ Background Radiant Beams */
export function BackgroundBeams({ className }: { className?: string }) {
  return (
    <div className={clsx("pointer-events-none absolute inset-0 overflow-hidden", className)}>
      <div className="absolute -top-[40%] left-[20%] h-[500px] w-[500px] rounded-full bg-emerald-500/10 blur-[120px] dark:bg-emerald-500/15" />
      <div className="absolute -top-[30%] right-[10%] h-[400px] w-[400px] rounded-full bg-teal-500/10 blur-[100px] dark:bg-teal-500/10" />
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-forest/30 to-transparent" />
    </div>
  );
}

/* ------------------------------------------------------------------ Floating Dock (Apple macOS style) */
export function FloatingDock({
  items,
  className,
}: {
  items: Array<{
    title: string;
    icon: ReactNode;
    href: string;
    badge?: number | string;
    active?: boolean;
    onClick?: () => void;
  }>;
  className?: string;
}) {
  return (
    <div
      className={clsx(
        "fixed bottom-5 left-1/2 -translate-x-1/2 z-40 flex items-center gap-2 p-2 rounded-2xl",
        "bg-surface/85 dark:bg-[#151a17]/85 backdrop-blur-2xl border border-line/80 shadow-2xl",
        className
      )}
    >
      {items.map((it, idx) => (
        <a
          key={idx}
          href={it.href}
          onClick={(e) => {
            if (it.onClick) {
              e.preventDefault();
              it.onClick();
            }
          }}
          title={it.title}
          className={clsx(
            "relative group flex items-center justify-center p-2.5 rounded-xl transition-all duration-200",
            it.active
              ? "bg-forest text-white shadow-md shadow-forest/25 scale-105"
              : "text-muted hover:text-ink hover:bg-surface-2 hover:scale-105"
          )}
        >
          {it.icon}
          {it.badge && (
            <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-critical text-[9px] font-bold text-white shadow-sm">
              {it.badge}
            </span>
          )}
          <span className="pointer-events-none absolute -top-8 rounded-lg bg-charcoal dark:bg-surface-2 px-2 py-0.5 text-[10px] font-semibold text-white opacity-0 transition-opacity group-hover:opacity-100 shadow-md whitespace-nowrap">
            {it.title}
          </span>
        </a>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ Aceternity Timeline Tree */
export function TimelineTree({
  items,
  className,
}: {
  items: Array<{
    title: string;
    description: string;
    timestamp: string;
    status?: "active" | "completed" | "pending" | "warning";
    tag?: string;
  }>;
  className?: string;
}) {
  return (
    <div className={clsx("relative space-y-6 pl-6 before:absolute before:left-[11px] before:top-2 before:bottom-2 before:w-[2px] before:bg-gradient-to-b before:from-forest before:via-emerald-400 before:to-line", className)}>
      {items.map((item, idx) => {
        const isCurrent = item.status === "active";
        return (
          <div key={idx} className="relative group">
            <div
              className={clsx(
                "absolute -left-[30px] top-1 h-4 w-4 rounded-full border-2 transition-all duration-300",
                isCurrent
                  ? "border-emerald-500 bg-forest shadow-md shadow-emerald-500/50 scale-125"
                  : item.status === "warning"
                  ? "border-amber-500 bg-amber-400"
                  : "border-line bg-surface dark:bg-[#1a211d] group-hover:border-forest"
              )}
            >
              {isCurrent && <div className="absolute inset-0 rounded-full bg-emerald-400 animate-ping opacity-60" />}
            </div>

            <div className="rounded-2xl bg-surface/80 dark:bg-surface/50 border border-line p-3.5 backdrop-blur-md hover:border-forest/40 transition duration-200">
              <div className="flex flex-wrap items-center justify-between gap-1.5 mb-1">
                <span className="text-xs font-bold text-ink">{item.title}</span>
                <div className="flex items-center gap-2">
                  {item.tag && (
                    <span className="font-mono text-[9px] px-1.5 py-0.5 rounded-md bg-forest-soft text-forest font-semibold">
                      {item.tag}
                    </span>
                  )}
                  <span className="font-mono text-[10px] text-muted">{item.timestamp}</span>
                </div>
              </div>
              <p className="text-xs text-muted leading-relaxed">{item.description}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
