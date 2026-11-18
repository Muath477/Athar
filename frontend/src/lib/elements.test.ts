import { describe, expect, it } from "vitest";
import { NO_PENDING, buildEdits, cellLabelAt, measureShape, pendingCount, withPending } from "@/lib/elements";
import type { GlossaryEntry, MapElement } from "@/lib/maps";

const WALL = { width_m: 8, height_m: 4 };
const GRID = { rows: 4, cols: 4 };
const glossary: Record<string, GlossaryEntry> = {
  crack: { damage_type: "crack", name_ar: "التشققات", geometry: "line", measure_ar: "", class_kind: "width", classes: [], color: "#b0357c", core: true },
  plaster_loss: { damage_type: "plaster_loss", name_ar: "فقدان اللياسة", geometry: "area", measure_ar: "", class_kind: null, classes: [], color: "#2f5ea8", core: true },
};

const existing: MapElement = {
  id: "E1",
  damage_type: "plaster_loss",
  geometry: "area",
  points: [[0, 0], [0.5, 0], [0.5, 0.5]],
  severity: "watch",
  confidence: "low",
  source: "model",
  damage_class: null,
  area_m2: 4,
  length_m: 0,
  count: 0,
  location: "A1",
  needs_review: true,
};

describe("element geometry", () => {
  it("measures areas, lengths and points in wall metres", () => {
    expect(measureShape("area", [[0, 0], [0.5, 0], [0.5, 0.5], [0, 0.5]], WALL).area_m2).toBe(8);
    expect(measureShape("line", [[0.5, 0], [0.5, 1]], WALL).length_m).toBe(4);
    expect(measureShape("point", [[0.2, 0.2]], WALL).count).toBe(1);
  });

  it("names the reference cell under a point", () => {
    expect(cellLabelAt(0.99, 0.99, 4, 4)).toBe("D4");
    expect(cellLabelAt(0.3, 0.1, 4, 4)).toBe("A2");
  });

  it("applies pending edits locally and sends them as one batch", () => {
    const pending = {
      added: { N1: { damage_type: "crack", points: [[0.5, 0], [0.5, 1]], severity: "urgent", damage_class: "over_5mm" } },
      updated: {},
      deleted: ["E1"],
    };
    const shown = withPending([existing], pending, glossary, WALL, GRID);
    expect(shown.map((e) => [e.id, e.geometry, e.length_m])).toEqual([["N1", "line", 4]]);
    expect(pendingCount(pending)).toBe(2);
    expect(buildEdits(pending).map((e) => e.action)).toEqual(["delete", "add"]);
    expect(pendingCount(NO_PENDING)).toBe(0);
  });
});
