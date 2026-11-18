import { ChevronDownIcon } from "lucide-react";
import type * as React from "react";
import { cn } from "@/lib/utils";
import { fieldClass } from "./input";

function NativeSelect({ className, ...props }: React.ComponentProps<"select">) {
  return (
    <span data-slot="native-select-wrapper" className="relative inline-flex w-full has-[select:disabled]:opacity-50">
      <select
        data-slot="native-select"
        className={cn(fieldClass, "min-h-11 cursor-pointer appearance-none ps-3 pe-9", className)}
        {...props}
      />
      <ChevronDownIcon
        aria-hidden="true"
        className="pointer-events-none absolute end-3 top-1/2 size-4 -translate-y-1/2 text-mud"
      />
    </span>
  );
}

export { NativeSelect };
