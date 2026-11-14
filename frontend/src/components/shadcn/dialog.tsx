import { createContext, useContext, useState, type ReactNode } from "react";
import { X } from "lucide-react";
import { cn } from "../../lib/utils";

interface DialogContextValue {
  open: boolean;
  setOpen: (open: boolean) => void;
}

const DialogContext = createContext<DialogContextValue | null>(null);

export function Dialog({
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
    <DialogContext.Provider value={{ open: isOpen, setOpen: handleOpenChange }}>
      {children}
    </DialogContext.Provider>
  );
}

export function DialogTrigger({ children }: { children: ReactNode }) {
  const ctx = useContext(DialogContext);
  if (!ctx) throw new Error("DialogTrigger must be used within Dialog");

  return (
    <div className="inline-block" onClick={() => ctx.setOpen(true)}>
      {children}
    </div>
  );
}

export function DialogContent({
  className,
  children,
}: {
  className?: string;
  children: ReactNode;
}) {
  const ctx = useContext(DialogContext);
  if (!ctx) throw new Error("DialogContent must be used within Dialog");
  if (!ctx.open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Apple Frosted Backdrop */}
      <div
        className="fixed inset-0 bg-charcoal/40 dark:bg-black/60 backdrop-blur-md transition-opacity animate-fadeIn"
        onClick={() => ctx.setOpen(false)}
      />

      {/* Modal Dialog Window */}
      <div
        className={cn(
          "relative z-50 w-full max-w-lg rounded-3xl border border-line bg-surface/95 dark:bg-[#191f1c]/95 backdrop-blur-2xl p-6 shadow-2xl animate-scaleUp overflow-hidden",
          className
        )}
      >
        {/* Top specular highlight */}
        <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/40 dark:via-white/10 to-transparent" />
        
        <button
          onClick={() => ctx.setOpen(false)}
          className="absolute right-4 top-4 rounded-xl p-1.5 text-muted hover:text-ink hover:bg-surface-2 transition"
          aria-label="Close dialog"
        >
          <X size={16} />
        </button>

        {children}
      </div>
    </div>
  );
}

export function DialogHeader({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("flex flex-col space-y-1.5 text-left mb-4", className)} {...props} />;
}

export function DialogTitle({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return <h2 className={cn("text-base font-bold tracking-tight text-ink", className)} {...props} />;
}

export function DialogDescription({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn("text-xs text-muted leading-relaxed", className)} {...props} />;
}

export function DialogFooter({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("flex flex-wrap items-center justify-end gap-2 pt-4 border-t border-line/60 mt-4", className)} {...props} />;
}
