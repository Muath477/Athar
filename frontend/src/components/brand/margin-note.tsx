import type * as React from "react";
import { cn } from "@/lib/utils";

type Props = React.ComponentProps<"aside"> & {
  label?: React.ReactNode;
};

export function MarginNote({ label = "حاشية", className, children, ...props }: Props) {
  return (
    <aside
      data-slot="margin-note"
      className={cn("flex flex-col gap-0.5 border-s-2 border-sadu ps-3 text-sm leading-relaxed text-sadu", className)}
      {...props}
    >
      <span className="text-xs font-bold">{label}</span>
      <div className="text-ink">{children}</div>
    </aside>
  );
}
