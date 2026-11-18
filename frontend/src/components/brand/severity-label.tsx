import { TriangleAlertIcon } from "lucide-react";
import { severityAr } from "@/lib/labels";
import { cn } from "@/lib/utils";

export function SeverityLabel({ severity, className }: { severity: string; className?: string }) {
  const urgent = severity === "urgent";
  return (
    <span className={cn("inline-flex items-center gap-1", urgent && "font-bold text-urgent", className)}>
      {urgent && <TriangleAlertIcon className="size-4 shrink-0" aria-hidden="true" />}
      {severityAr[severity] ?? severity}
    </span>
  );
}
