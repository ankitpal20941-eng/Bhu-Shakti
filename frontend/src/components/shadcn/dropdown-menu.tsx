import { createContext, useContext, useState, type ReactNode } from "react";
import { cn } from "../../lib/utils";

interface DropdownContextValue {
  open: boolean;
  setOpen: (open: boolean) => void;
}

const DropdownContext = createContext<DropdownContextValue | null>(null);

export function DropdownMenu({
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
    <DropdownContext.Provider value={{ open: isOpen, setOpen: handleOpenChange }}>
      <div className="relative inline-block text-left">{children}</div>
    </DropdownContext.Provider>
  );
}

export function DropdownMenuTrigger({ children }: { children: ReactNode }) {
  const ctx = useContext(DropdownContext);
  if (!ctx) throw new Error("DropdownMenuTrigger must be used within DropdownMenu");

  return (
    <div className="inline-block cursor-pointer" onClick={() => ctx.setOpen(!ctx.open)}>
      {children}
    </div>
  );
}

export function DropdownMenuContent({
  className,
  align = "right",
  children,
}: {
  className?: string;
  align?: "left" | "right";
  children: ReactNode;
}) {
  const ctx = useContext(DropdownContext);
  if (!ctx) throw new Error("DropdownMenuContent must be used within DropdownMenu");
  if (!ctx.open) return null;

  return (
    <>
      <div className="fixed inset-0 z-[60]" onClick={() => ctx.setOpen(false)} />
      <div
        className={cn(
          "absolute z-[70] mt-2 min-w-[14rem] rounded-2xl border border-line/80 bg-white dark:bg-[#181e1a] p-2.5 text-ink shadow-[0_25px_60px_-15px_rgba(0,0,0,0.3)] ring-1 ring-black/10 dark:ring-white/10 animate-scaleUp overflow-hidden backdrop-blur-none",
          align === "right" ? "right-0" : "left-0",
          className
        )}
      >
        {children}
      </div>
    </>
  );
}

export function DropdownMenuItem({
  className,
  onClick,
  children,
}: {
  className?: string;
  onClick?: () => void;
  children: ReactNode;
}) {
  const ctx = useContext(DropdownContext);

  const handleClick = () => {
    onClick?.();
    ctx?.setOpen(false);
  };

  return (
    <button
      onClick={handleClick}
      className={cn(
        "relative flex w-full cursor-pointer select-none items-center gap-2 rounded-xl px-3 py-2 text-xs font-medium outline-none transition-colors hover:bg-surface-2 focus:bg-surface-2",
        className
      )}
    >
      {children}
    </button>
  );
}

export function DropdownMenuLabel({ className, children }: { className?: string; children: ReactNode }) {
  return (
    <div className={cn("px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-muted font-mono", className)}>
      {children}
    </div>
  );
}

export function DropdownMenuSeparator({ className }: { className?: string }) {
  return <div className={cn("-mx-1 my-1 h-px bg-line/80", className)} />;
}
