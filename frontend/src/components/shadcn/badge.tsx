import { type HTMLAttributes } from "react";
import { cn } from "../../lib/utils";

export interface BadgeProps extends HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "secondary" | "destructive" | "outline" | "success" | "warning" | "watch";
}

export function Badge({ className, variant = "default", children, ...props }: BadgeProps) {
  return (
    <div
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[10px] font-bold font-mono tracking-wide uppercase transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 border",
        variant === "default" && "border-forest/30 bg-forest-soft text-forest",
        variant === "secondary" && "border-line bg-surface-2 text-ink",
        variant === "destructive" && "border-critical/30 bg-critical/10 text-critical",
        variant === "warning" && "border-warning/30 bg-warning/10 text-warning",
        variant === "watch" && "border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400",
        variant === "success" && "border-safe/30 bg-safe/10 text-safe",
        variant === "outline" && "border-line text-muted bg-transparent",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}
