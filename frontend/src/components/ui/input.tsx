import type * as React from "react";
import { cn } from "@/lib/utils";

const fieldClass =
  "w-full min-w-0 rounded-sm border border-input bg-white px-3 text-base text-ink transition-colors duration-150 placeholder:text-mud/80 hover:border-ink focus-visible:border-ring disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-destructive aria-invalid:bg-destructive/5";

function Input({ className, type, ...props }: React.ComponentProps<"input">) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        fieldClass,
        "min-h-11 file:me-3 file:min-h-9 file:border-0 file:bg-transparent file:font-bold file:text-ink",
        className,
      )}
      {...props}
    />
  );
}

export { Input, fieldClass };
