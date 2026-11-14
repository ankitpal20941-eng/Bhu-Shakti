import { useState, type ReactNode } from "react";
import { cn } from "../../lib/utils";

export function Avatar({ className, children }: { className?: string; children: ReactNode }) {
  return (
    <div
      className={cn(
        "relative flex h-8 w-8 shrink-0 overflow-hidden rounded-xl border border-line bg-surface-2 text-ink shadow-sm",
        className
      )}
    >
      {children}
    </div>
  );
}

export function AvatarImage({ src, alt, className }: { src: string; alt?: string; className?: string }) {
  const [error, setError] = useState(false);
  if (error) return null;

  return (
    <img
      src={src}
      alt={alt || "Avatar"}
      onError={() => setError(true)}
      className={cn("aspect-square h-full w-full object-cover", className)}
    />
  );
}

export function AvatarFallback({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={cn(
        "flex h-full w-full items-center justify-center rounded-xl bg-forest-soft text-forest text-xs font-bold font-mono uppercase",
        className
      )}
    >
      {children}
    </div>
  );
}
