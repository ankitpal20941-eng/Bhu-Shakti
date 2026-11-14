import { type HTMLAttributes } from "react";
import { cn } from "../../lib/utils";

export function Separator({
  className,
  orientation = "horizontal",
  ...props
}: HTMLAttributes<HTMLDivElement> & { orientation?: "horizontal" | "vertical" }) {
  return (
    <div
      role="separator"
      className={cn(
        "shrink-0 bg-line/80",
        orientation === "horizontal" ? "h-[1px] w-full my-3" : "h-full w-[1px] mx-2",
        className
      )}
      {...props}
    />
  );
}
