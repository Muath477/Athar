"use client";

import { Direction } from "radix-ui";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <Direction.Provider dir="rtl">
      <TooltipProvider>
        {children}
        <Toaster />
      </TooltipProvider>
    </Direction.Provider>
  );
}
