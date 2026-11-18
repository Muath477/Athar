"use client";

import { distanceAr } from "@/lib/directions";
import { ManeuverArrow } from "./maneuver-arrow";
import type { RouteStep } from "./use-route-to-site";

type Props = { steps: RouteStep[]; currentIndex: number | null; onFocusStep: (index: number) => void };

export function RouteSteps({ steps, currentIndex, onFocusStep }: Props) {
  if (steps.length === 0) return null;

  return (
    <details className="group rounded-sm border border-line" open>
      <summary className="flex min-h-11 cursor-pointer items-center px-3 font-bold">خطوات الطريق ({steps.length})</summary>
      <ol className="flex flex-col border-t border-line">
        {steps.map((step, index) => {
          const current = index === currentIndex;
          return (
            <li key={index} aria-current={current ? "step" : undefined}>
              <button
                onClick={() => onFocusStep(index)}
                className={`flex w-full items-start gap-3 px-3 py-2.5 text-start ${current ? "bg-mud text-sand" : ""}`}
              >
                <ManeuverArrow maneuver={step.maneuver} className="mt-0.5 size-5 shrink-0" />
                <span className="flex-1 leading-relaxed">{step.instruction}</span>
                <span className="shrink-0 text-xs tabular-nums opacity-80">{distanceAr(step.distanceMeters)}</span>
              </button>
            </li>
          );
        })}
      </ol>
    </details>
  );
}
