import { describe, expect, it } from "vitest";
import { bearingDegrees, metersBetween, pointAhead, projectOntoPath, remainingMeters, sampleAlong } from "./route-geometry";

const west = { lat: 24.7336, lng: 46.573 };
const corner = { lat: 24.7336, lng: 46.583 };
const north = { lat: 24.7426, lng: 46.583 };
const path = [west, corner, north];

describe("route geometry", () => {
  it("measures about one kilometre between points 0.01° apart near Riyadh", () => {
    expect(metersBetween(west, corner)).toBeCloseTo(1009.9, 0);
    expect(metersBetween(corner, north)).toBeCloseTo(1000.8, 0);
  });

  it("gives compass bearings", () => {
    expect(bearingDegrees(west, corner)).toBeCloseTo(90, 1);
    expect(bearingDegrees(corner, north)).toBeCloseTo(0, 1);
  });

  it("snaps a position beside the path onto the nearest segment", () => {
    const projection = projectOntoPath(path, { lat: 24.734, lng: 46.578 });
    expect(projection.segment).toBe(0);
    expect(projection.fraction).toBeCloseTo(0.5, 2);
    expect(projection.offsetMeters).toBeCloseTo(44.5, 0);
  });

  it("counts the distance still to walk from the snapped point", () => {
    const projection = projectOntoPath(path, { lat: 24.734, lng: 46.578 });
    expect(remainingMeters(path, projection)).toBeCloseTo(metersBetween(west, corner) / 2 + metersBetween(corner, north), 0);
    expect(remainingMeters(path, projectOntoPath(path, { lat: 24.75, lng: 46.583 }))).toBeCloseTo(0, 5);
  });

  it("looks ahead around a corner", () => {
    const projection = projectOntoPath(path, { lat: 24.7336, lng: 46.578 });
    const ahead = pointAhead(path, projection, metersBetween(west, corner) / 2 + 100);
    expect(bearingDegrees(corner, ahead)).toBeCloseTo(0, 1);
    expect(metersBetween(corner, ahead)).toBeCloseTo(100, 0);
  });

  it("samples evenly by distance and keeps both ends", () => {
    const samples = sampleAlong(path, 5);
    expect(samples).toHaveLength(5);
    expect(metersBetween(samples[0], west)).toBeLessThan(0.01);
    expect(metersBetween(samples[4], north)).toBeLessThan(0.01);
  });

  it("handles a single-point path", () => {
    expect(projectOntoPath([west], corner).offsetMeters).toBeCloseTo(1009.9, 0);
    expect(sampleAlong([west], 5)).toEqual([west]);
  });
});
