import { type SVGProps } from "react";
import clsx from "clsx";

interface BhuShaktiLogoProps extends SVGProps<SVGSVGElement> {
  size?: number | string;
  variant?: "mark" | "full" | "monochrome";
  className?: string;
  showSubtitle?: boolean;
}

/**
 * BhuShaktiLogo
 *
 * Distinctive brand icon representing:
 * - "Bhu" (भू / Earth): Himalayan mountain ridges and geological slope strata
 * - "Shakti" (शक्ति / Protective Power): Geometric shield aegis guarding communities
 * - "AI": Telemetry radar beacon, sensor waves, and early-warning pulse
 */
export function BhuShaktiLogoMark({ size = 36, className }: { size?: number | string; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={clsx("shrink-0 select-none", className)}
      aria-label="BhuShakti AI Emblem"
    >
      <defs>
        {/* Background Apple-grade squircle gradient */}
        <linearGradient id="bsBgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#0d3b2e" />
          <stop offset="50%" stopColor="#064e3b" />
          <stop offset="100%" stopColor="#022c22" />
        </linearGradient>

        {/* Specular edge highlight */}
        <linearGradient id="bsSpecular" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="#34d399" stopOpacity="0.6" />
          <stop offset="40%" stopColor="#10b981" stopOpacity="0.1" />
          <stop offset="100%" stopColor="#047857" stopOpacity="0.3" />
        </linearGradient>

        {/* Primary mountain slope gradient */}
        <linearGradient id="bsMountainMain" x1="20%" y1="0%" x2="80%" y2="100%">
          <stop offset="0%" stopColor="#ecfdf5" />
          <stop offset="100%" stopColor="#a7f3d0" />
        </linearGradient>

        {/* Secondary shaded mountain ridge */}
        <linearGradient id="bsMountainShade" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#6ee7b7" />
          <stop offset="100%" stopColor="#059669" />
        </linearGradient>

        {/* Third background ridge */}
        <linearGradient id="bsMountainBack" x1="50%" y1="0%" x2="50%" y2="100%">
          <stop offset="0%" stopColor="#34d399" stopOpacity="0.5" />
          <stop offset="100%" stopColor="#047857" stopOpacity="0.8" />
        </linearGradient>

        {/* Radar beacon glow */}
        <linearGradient id="bsRadarPulse" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#fbbf24" />
          <stop offset="100%" stopColor="#f59e0b" />
        </linearGradient>

        {/* Soft shadow filter */}
        <filter id="bsShadow" x="-10%" y="-10%" width="120%" height="120%">
          <feDropShadow dx="0" dy="2" stdDeviation="2.5" floodColor="#022c22" floodOpacity="0.4" />
        </filter>
      </defs>

      {/* Outer Squircle Container */}
      <rect
        x="2"
        y="2"
        width="96"
        height="96"
        rx="24"
        fill="url(#bsBgGrad)"
        stroke="url(#bsSpecular)"
        strokeWidth="1.5"
      />

      {/* Subtle Contour Grid / Iso-elevation rings (Subsurface Telemetry) */}
      <path
        d="M12 76 C 30 70, 70 70, 88 76"
        stroke="#10b981"
        strokeOpacity="0.25"
        strokeWidth="1"
        strokeDasharray="2 2"
      />
      <path
        d="M16 83 C 35 78, 65 78, 84 83"
        stroke="#10b981"
        strokeOpacity="0.18"
        strokeWidth="1"
        strokeDasharray="2 2"
      />

      {/* AI Radar telemetry arcs emanating from the summit sensor */}
      <path
        d="M38 27 C 45 22, 55 22, 62 27"
        stroke="#fbbf24"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeOpacity="0.75"
      />
      <path
        d="M33 21 C 43 14, 57 14, 67 21"
        stroke="#fbbf24"
        strokeWidth="1.4"
        strokeLinecap="round"
        strokeOpacity="0.45"
      />

      {/* Background Mountain Ridge */}
      <path
        d="M48 36 L68 62 L82 78 L48 78 Z"
        fill="url(#bsMountainBack)"
      />

      {/* Main Mountain Peak (Forefront - West Face / Sunlight) */}
      <path
        d="M50 32 L22 78 L50 78 Z"
        fill="url(#bsMountainMain)"
        filter="url(#bsShadow)"
      />

      {/* Main Mountain Peak (East Face / Shadowed Slope with Ridge Cleavage) */}
      <path
        d="M50 32 L50 78 L68 78 L78 64 Z"
        fill="url(#bsMountainShade)"
        opacity="0.9"
      />

      {/* Geological Fault / Slope Contour Line */}
      <path
        d="M50 32 L40 56 L50 78"
        stroke="#047857"
        strokeWidth="1.2"
        strokeLinecap="round"
        strokeOpacity="0.7"
      />

      {/* Protective Shield Contour (Shakti Aegis Base) */}
      <path
        d="M20 78 Q 50 90, 80 78"
        stroke="#34d399"
        strokeWidth="2.5"
        strokeLinecap="round"
      />

      {/* AI Summit Telemetry Sensor Dot */}
      <circle cx="50" cy="32" r="3.2" fill="url(#bsRadarPulse)" />
      <circle cx="50" cy="32" r="5" stroke="#fbbf24" strokeWidth="1" strokeOpacity="0.5" />
    </svg>
  );
}

export function BhuShaktiLogo({
  size = 38,
  variant = "full",
  className,
  showSubtitle = true,
}: BhuShaktiLogoProps) {
  if (variant === "mark") {
    return <BhuShaktiLogoMark size={size} className={className} />;
  }

  return (
    <div className={clsx("flex items-center gap-2.5 select-none", className)}>
      <BhuShaktiLogoMark size={size} />
      <div className="flex flex-col">
        <div className="flex items-center gap-1.5 leading-none">
          <span className="text-sm font-black tracking-tight text-ink font-heading">
            BHUSHAKTI
          </span>
          <span className="bg-forest/15 dark:bg-forest/30 border border-forest/30 text-forest dark:text-emerald-300 text-[10px] font-black px-1.5 py-0.5 rounded-md tracking-wider">
            AI
          </span>
        </div>
        {showSubtitle && (
          <span className="text-[10px] text-muted font-medium tracking-tight mt-0.5">
            Landslide Early Warning System
          </span>
        )}
      </div>
    </div>
  );
}
