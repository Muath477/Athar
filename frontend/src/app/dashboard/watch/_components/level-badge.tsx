import { TriangleAlertIcon } from "lucide-react";
import type { ComponentProps, ReactNode } from "react";
import { Badge } from "@/components/ui/badge";
import { type RiskLevel, levelAr } from "@/lib/watch";

const LEVEL_BADGE: Record<RiskLevel, ComponentProps<typeof Badge>["variant"]> = {
  unknown: "outline",
  stable: "muted",
  watch: "watch",
  moderate: "moderate",
  urgent: "urgent",
};

export function LevelBadge({ level, children }: { level: RiskLevel; children?: ReactNode }) {
  return (
    <Badge variant={LEVEL_BADGE[level]}>
      {level === "urgent" && <TriangleAlertIcon aria-hidden="true" />}
      {children ?? levelAr[level]}
    </Badge>
  );
}

export function SampleBadge({ children }: { children: ReactNode }) {
  return (
    <Badge variant="outline" className="border-dashed">
      {children}
    </Badge>
  );
}
