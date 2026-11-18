import {
  bearingDegrees,
  metersBetween,
  type Point,
  pointAhead,
  projectOntoPath,
  remainingMeters,
} from "@/lib/route-geometry";
import type { PlannedRoute, RouteStep } from "./use-route-to-site";

export const OFF_ROUTE_METERS = 40;
export const ARRIVAL_METERS = 30;
const LOOK_AHEAD_METERS = 25;
const STEP_TIE_METERS = 3;

export type RouteProgress = {
  snapped: Point;
  travelled: Point[];
  ahead: Point[];
  remainingMeters: number;
  offRoute: boolean;
  arrived: boolean;
  heading: number;
  stepIndex: number;
  nextStep: RouteStep | null;
  metersToNextStep: number;
};

export function routeProgress(route: PlannedRoute, position: Point, destination: Point): RouteProgress {
  const projection = projectOntoPath(route.path, position);
  const remaining = remainingMeters(route.path, projection);
  const offRoute = projection.offsetMeters > OFF_ROUTE_METERS;
  const stepIndex = currentStepIndex(route.steps, position);
  const nextStep = route.steps[stepIndex + 1] ?? null;

  return {
    snapped: projection.point,
    travelled: [...route.path.slice(0, projection.segment + 1), projection.point],
    ahead: [projection.point, ...route.path.slice(projection.segment + 1)],
    remainingMeters: remaining,
    offRoute,
    arrived: metersBetween(position, destination) <= ARRIVAL_METERS || (!offRoute && remaining <= ARRIVAL_METERS),
    heading: bearingDegrees(projection.point, pointAhead(route.path, projection, LOOK_AHEAD_METERS)),
    stepIndex,
    nextStep,
    metersToNextStep: metersBetween(position, nextStep?.start ?? destination),
  };
}

export function currentStepIndex(steps: RouteStep[], position: Point): number {
  let best = 0;
  let bestOffset = Number.POSITIVE_INFINITY;
  steps.forEach((step, index) => {
    if (step.path.length === 0) return;
    const offset = projectOntoPath(step.path, position).offsetMeters;
    const asCloseAsBest = offset <= bestOffset + STEP_TIE_METERS;
    if (asCloseAsBest) {
      best = index;
      bestOffset = Math.min(offset, bestOffset);
    }
  });
  return best;
}
