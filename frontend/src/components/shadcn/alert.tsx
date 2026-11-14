import { forwardRef, type HTMLAttributes } from "react";
import { AlertCircle, AlertTriangle, CheckCircle2, Info } from "lucide-react";
import { cn } from "../../lib/utils";

export interface AlertProps extends HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "destructive" | "warning" | "success" | "info";
}

export const Alert = forwardRef<HTMLDivElement, AlertProps>(
  ({ className, variant = "default", children, ...props }, ref) => (
    <div
      ref={ref}
      role="alert"
      className={cn(
        "relative w-full rounded-2xl border p-4 text-xs transition-all flex items-start gap-3 backdrop-blur-md",
        variant === "default" && "bg-surface-2/80 border-line text-ink",
        variant === "destructive" && "border-critical/30 bg-critical/5 text-critical",
        variant === "warning" && "border-warning/30 bg-warning/5 text-warning",
        variant === "success" && "border-safe/30 bg-safe/5 text-safe",
        variant === "info" && "border-subtle/30 bg-subtle/5 text-subtle",
        className
      )}
      {...props}
    >
      <div className="shrink-0 mt-0.5">
        {variant === "destructive" && <AlertCircle size={16} />}
        {variant === "warning" && <AlertTriangle size={16} />}
        {variant === "success" && <CheckCircle2 size={16} />}
        {variant === "info" && <Info size={16} />}
        {variant === "default" && <Info size={16} className="text-forest" />}
      </div>
      <div className="flex-1 space-y-1">{children}</div>
    </div>
  )
);
Alert.displayName = "Alert";

export const AlertTitle = forwardRef<HTMLParagraphElement, HTMLAttributes<HTMLHeadingElement>>(
  ({ className, ...props }, ref) => (
    <h5 ref={ref} className={cn("font-bold text-ink leading-tight", className)} {...props} />
  )
);
AlertTitle.displayName = "AlertTitle";

export const AlertDescription = forwardRef<HTMLParagraphElement, HTMLAttributes<HTMLParagraphElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("text-xs text-muted leading-relaxed font-normal", className)} {...props} />
  )
);
AlertDescription.displayName = "AlertDescription";
