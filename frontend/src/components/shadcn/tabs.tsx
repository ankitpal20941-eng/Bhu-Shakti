import { createContext, useContext, useState, type ReactNode } from "react";
import { cn } from "../../lib/utils";

interface TabsContextValue {
  value: string;
  onValueChange: (val: string) => void;
}

const TabsContext = createContext<TabsContextValue | null>(null);

export function Tabs({
  value,
  defaultValue,
  onValueChange,
  className,
  children,
}: {
  value?: string;
  defaultValue?: string;
  onValueChange?: (val: string) => void;
  className?: string;
  children: ReactNode;
}) {
  const [internalVal, setInternalVal] = useState(defaultValue || "");
  const activeValue = value !== undefined ? value : internalVal;
  const handleChange = (val: string) => {
    setInternalVal(val);
    onValueChange?.(val);
  };

  return (
    <TabsContext.Provider value={{ value: activeValue, onValueChange: handleChange }}>
      <div className={cn("space-y-4", className)}>{children}</div>
    </TabsContext.Provider>
  );
}

export function TabsList({ className, children }: { className?: string; children: ReactNode }) {
  return (
    <div
      className={cn(
        "inline-flex h-9 items-center justify-center rounded-xl bg-surface-2/80 dark:bg-surface-2/50 backdrop-blur-md p-1 border border-line text-muted",
        className
      )}
    >
      {children}
    </div>
  );
}

export function TabsTrigger({
  value,
  className,
  children,
  disabled,
}: {
  value: string;
  className?: string;
  children: ReactNode;
  disabled?: boolean;
}) {
  const ctx = useContext(TabsContext);
  if (!ctx) throw new Error("TabsTrigger must be used within Tabs");
  const isSelected = ctx.value === value;

  return (
    <button
      disabled={disabled}
      onClick={() => ctx.onValueChange(value)}
      className={cn(
        "inline-flex items-center justify-center whitespace-nowrap rounded-lg px-3 py-1 text-xs font-medium ring-offset-background transition-all focus-visible:outline-none disabled:pointer-events-none disabled:opacity-50",
        isSelected
          ? "bg-surface text-ink font-semibold shadow-sm border border-line/60"
          : "text-muted hover:text-ink hover:bg-surface/50",
        className
      )}
    >
      {children}
    </button>
  );
}

export function TabsContent({
  value,
  className,
  children,
}: {
  value: string;
  className?: string;
  children: ReactNode;
}) {
  const ctx = useContext(TabsContext);
  if (!ctx) throw new Error("TabsContent must be used within Tabs");
  if (ctx.value !== value) return null;

  return (
    <div
      className={cn(
        "ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-forest/50 focus-visible:ring-offset-2 animate-fadeIn",
        className
      )}
    >
      {children}
    </div>
  );
}
