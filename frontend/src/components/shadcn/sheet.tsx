import React, { createContext, useContext, useState, type ReactNode } from "react";
import { X } from "lucide-react";
import { cn } from "../../lib/utils";

interface SheetContextValue {
  open: boolean;
  setOpen: (open: boolean) => void;
}

const SheetContext = createContext<SheetContextValue | null>(null);

export function Sheet({
  open,
  defaultOpen = false,
  onOpenChange,
  children,
}: {
  open?: boolean;
  defaultOpen?: boolean;
  onOpenChange?: (open: boolean) => void;
  children: ReactNode;
}) {
  const [internalOpen, setInternalOpen] = useState(defaultOpen);
  const isOpen = open !== undefined ? open : internalOpen;

  const handleOpenChange = (newVal: boolean) => {
    setInternalOpen(newVal);
    onOpenChange?.(newVal);
  };

  return (
    <SheetContext.Provider value={{ open: isOpen, setOpen: handleOpenChange }}>
      {children}
    </SheetContext.Provider>
  );
}

export function SheetTrigger({ children }: { children: ReactNode }) {
  const ctx = useContext(SheetContext);
  if (!ctx) throw new Error("SheetTrigger must be used within Sheet");

  return (
    <div className="inline-block cursor-pointer" onClick={() => ctx.setOpen(true)}>
      {children}
    </div>
  );
}

export function SheetContent({
  className,
  side = "right",
  children,
}: {
  className?: string;
  side?: "right" | "left";
  children: ReactNode;
}) {
  const ctx = useContext(SheetContext);
  if (!ctx) throw new Error("SheetContent must be used within Sheet");
  if (!ctx.open) return null;

  return (
    <div className="fixed inset-0 z-50">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-charcoal/40 dark:bg-black/60 backdrop-blur-sm transition-opacity"
        onClick={() => ctx.setOpen(false)}
      />

      {/* Slide-out Sheet */}
      <div
        className={cn(
          "fixed inset-y-0 z-50 flex w-full max-w-md flex-col bg-surface/95 dark:bg-[#191f1c]/95 backdrop-blur-2xl border-line p-6 shadow-2xl transition ease-in-out duration-300",
          side === "right" ? "right-0 border-l animate-slideLeft" : "left-0 border-r animate-slideRight",
          className
        )}
      >
        <button
          onClick={() => ctx.setOpen(false)}
          className="absolute right-4 top-4 rounded-xl p-1.5 text-muted hover:text-ink hover:bg-surface-2 transition"
          aria-label="Close sheet"
        >
          <X size={16} />
        </button>
        {children}
      </div>
    </div>
  );
}

export function SheetHeader({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("flex flex-col space-y-1.5 text-left pb-4 border-b border-line/60 mb-4", className)} {...props} />;
}

export function SheetTitle({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return <h2 className={cn("text-base font-bold tracking-tight text-ink", className)} {...props} />;
}

export function SheetDescription({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn("text-xs text-muted leading-relaxed", className)} {...props} />;
}
