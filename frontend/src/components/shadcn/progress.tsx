import { type HTMLAttributes } from "react";
import { cn } from "../../lib/utils";

export interface ProgressProps extends HTMLAttributes<HTMLDivElement> {
  value?: number;
  max?: number;
  indicatorColor?: string;
}

export function Progress({
  className,
  value = 0,
  max = 100,
  indicatorColor,
  ...props
}: ProgressProps) {
  const percentage = Math.min(100, Math.max(0, (value / max) * 100));

  return (
    <div
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={max}
      aria-valuenow={value}
      className={cn(
        "relative h-2 w-full overflow-hidden rounded-full bg-surface-3/80 dark:bg-surface-3/40 border border-line/40",
        className
      )}
      {...props}
    >
      <div
        className={cn(
          "h-full rounded-full transition-all duration-500 ease-out",
          indicatorColor || "bg-forest"
        )}
        style={{ width: `${percentage}%` }}
      />
    </div>
  );
}
