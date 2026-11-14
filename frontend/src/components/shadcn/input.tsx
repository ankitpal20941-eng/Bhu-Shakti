import { forwardRef, type InputHTMLAttributes } from "react";
import { cn } from "../../lib/utils";

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, type = "text", ...props }, ref) => {
    return (
      <input
        type={type}
        ref={ref}
        className={cn(
          "flex h-9 w-full rounded-xl border border-line bg-surface/90 dark:bg-surface/70 backdrop-blur-md px-3 py-1.5 text-xs text-ink shadow-sm transition duration-150 placeholder:text-muted/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-forest/50 focus-visible:border-forest/60 disabled:cursor-not-allowed disabled:opacity-50",
          className
        )}
        {...props}
      />
    );
  }
);
Input.displayName = "Input";
