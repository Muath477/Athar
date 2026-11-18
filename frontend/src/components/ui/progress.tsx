"use client";

import { Progress as ProgressPrimitive } from "radix-ui";
import type * as React from "react";
import { cn } from "@/lib/utils";

function Progress({ className, value, ...props }: React.ComponentProps<typeof ProgressPrimitive.Root>) {
  const share = Math.min(Math.max(value ?? 0, 0), 100);
  return (
    <ProgressPrimitive.Root
      data-slot="progress"
      value={value}
      className={cn("relative h-1.5 w-full overflow-hidden rounded-xs bg-clay", className)}
      {...props}
    >
      <ProgressPrimitive.Indicator
        data-slot="progress-indicator"
        className="h-full bg-sadu transition-[inline-size] duration-200 ease-quill"
        style={{ inlineSize: `${share}%` }}
      />
    </ProgressPrimitive.Root>
  );
}

export { Progress };
