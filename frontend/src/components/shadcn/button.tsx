import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "../../lib/utils";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "destructive" | "outline" | "secondary" | "ghost" | "glass" | "pill";
  size?: "default" | "sm" | "lg" | "icon";
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "default", children, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center whitespace-nowrap text-xs font-semibold ring-offset-background transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-forest/50 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 active:scale-[0.98]",
          // Variants
          variant === "default" && "bg-forest text-white shadow-sm hover:brightness-105 active:brightness-95",
          variant === "destructive" && "bg-critical text-white shadow-sm hover:bg-critical/90",
          variant === "outline" && "border border-line bg-surface text-ink hover:bg-surface-2",
          variant === "secondary" && "bg-surface-2 text-ink border border-line/60 hover:bg-surface",
          variant === "ghost" && "text-muted hover:text-ink hover:bg-surface-2/60",
          variant === "glass" && "bg-surface/80 dark:bg-surface/60 backdrop-blur-xl border border-line/80 text-ink shadow-sm hover:border-forest/40 hover:bg-surface",
          variant === "pill" && "rounded-full bg-surface-2 border border-line text-ink hover:border-forest/50 px-4",
          // Sizes
          size === "default" && "h-8 px-3.5 py-1.5 rounded-xl",
          size === "sm" && "h-7 px-2.5 text-[11px] rounded-lg",
          size === "lg" && "h-10 px-5 text-sm rounded-2xl",
          size === "icon" && "h-8 w-8 rounded-xl",
          className
        )}
        {...props}
      >
        {children}
      </button>
    );
  }
);
Button.displayName = "Button";
