import { distanceAr } from "@/lib/directions";
import { ManeuverArrow } from "./maneuver-arrow";
import type { RouteProgress } from "./route-progress";

export function NextTurn({ progress, siteName }: { progress: RouteProgress; siteName: string }) {
  const { nextStep } = progress;
  const instruction = nextStep ? nextStep.instruction : `${siteName} أمامك`;

  return (
    <div className="absolute inset-x-3 bottom-3 flex items-center gap-3 rounded-xl bg-ink/90 p-3 text-sand shadow">
      <ManeuverArrow maneuver={nextStep?.maneuver ?? "DESTINATION"} className="size-9 shrink-0" />
      <div className="flex flex-col">
        <span className="text-lg font-bold tabular-nums">بعد {distanceAr(progress.metersToNextStep)}</span>
        <span aria-live="polite" className="leading-snug">
          {instruction}
        </span>
      </div>
    </div>
  );
}
