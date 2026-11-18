import { describe, expect, it } from "vitest";
import { currentStepIndex, routeProgress } from "./route-progress";
import type { PlannedRoute, RouteStep } from "./use-route-to-site";

const start = { lat: 24.7336, lng: 46.573 };
const corner = { lat: 24.7336, lng: 46.583 };
const site = { lat: 24.7426, lng: 46.583 };

const steps: RouteStep[] = [
  { instruction: "اتجه شرقًا", maneuver: "DEPART", distanceMeters: 1010, start, path: [start, corner] },
  { instruction: "انعطف يسارًا", maneuver: "TURN_LEFT", distanceMeters: 1001, start: corner, path: [corner, site] },
];
const route: PlannedRoute = {
  mode: "walking",
  origin: start,
  path: [start, corner, site],
  steps,
  distanceMeters: 2011,
  durationMillis: 1_500_000,
};

describe("route progress", () => {
  it("shows the next turn and its distance while on the first street", () => {
    const progress = routeProgress(route, { lat: 24.7336, lng: 46.578 }, site);
    expect(progress.stepIndex).toBe(0);
    expect(progress.nextStep?.instruction).toBe("انعطف يسارًا");
    expect(progress.metersToNextStep).toBeCloseTo(505, -1);
    expect(progress.offRoute).toBe(false);
    expect(Math.round(progress.heading)).toBe(90);
  });

  it("moves to the next step at the corner and points at the site", () => {
    const progress = routeProgress(route, corner, site);
    expect(progress.stepIndex).toBe(1);
    expect(progress.nextStep).toBeNull();
    expect(Math.round(progress.heading)).toBe(0);
  });

  it("flags leaving the route beyond 40 metres", () => {
    expect(routeProgress(route, { lat: 24.735, lng: 46.578 }, site).offRoute).toBe(true);
    expect(routeProgress(route, { lat: 24.7338, lng: 46.578 }, site).offRoute).toBe(false);
  });

  it("calls it arrived within 30 metres of the site", () => {
    expect(routeProgress(route, { lat: 24.7424, lng: 46.583 }, site).arrived).toBe(true);
    expect(routeProgress(route, { lat: 24.738, lng: 46.583 }, site).arrived).toBe(false);
  });

  it("splits the path into the part walked and the part ahead", () => {
    const progress = routeProgress(route, { lat: 24.738, lng: 46.583 }, site);
    expect(progress.travelled.at(-1)).toEqual(progress.ahead[0]);
    expect(progress.ahead.at(-1)).toEqual(site);
  });

  it("ignores steps without a path", () => {
    expect(currentStepIndex([{ ...steps[0], path: [] }, steps[1]], start)).toBe(1);
  });
});
