import type { ElementEdit, ElementShape, Geometry, GlossaryEntry, MapElement } from "@/lib/maps";

export const MIN_POINTS: Record<Geometry, number> = { area: 3, line: 2, point: 1 };

export const classAr: Record<string, string> = {
  under_1mm: "أقل من ١ ملم",
  from_1_to_5mm: "من ١ إلى ٥ ملم",
  over_5mm: "أكثر من ٥ ملم",
  shallow: "سطحي",
  medium: "متوسط",
  deep: "عميق",
  small: "صغير",
  large: "كبير",
};

export const classKindAr: Record<string, string> = { width: "فئة العرض", depth: "فئة العمق", size: "الحجم" };

export const geometryAr: Record<Geometry, string> = { area: "مضلع", line: "خط", point: "نقطة" };

export type Wall = { width_m: number; height_m: number };

export function measureShape(geometry: Geometry, points: number[][], wall: Wall) {
  const metres = points.map(([x, y]) => [x * wall.width_m, y * wall.height_m]);
  if (geometry === "point") return { area_m2: 0, length_m: 0, count: 1 };
  if (geometry === "line") {
    let length = 0;
    for (let i = 1; i < metres.length; i++) {
      length += Math.hypot(metres[i][0] - metres[i - 1][0], metres[i][1] - metres[i - 1][1]);
    }
    return { area_m2: 0, length_m: round(length), count: 0 };
  }
  let twice = 0;
  for (let i = 0; i < metres.length; i++) {
    const [x0, y0] = metres[i];
    const [x1, y1] = metres[(i + 1) % metres.length];
    twice += x0 * y1 - x1 * y0;
  }
  return { area_m2: round(Math.abs(twice) / 2), length_m: 0, count: 0 };
}

export function measureAr(element: Pick<MapElement, "area_m2" | "length_m" | "count" | "geometry">): string {
  const format = (value: number) => value.toLocaleString("ar-SA", { maximumFractionDigits: 2 });
  if (element.geometry === "point") return `${format(element.count)} نقطة`;
  if (element.geometry === "line") return `${format(element.length_m)} م`;
  return `${format(element.area_m2)} م²`;
}

export function cellLabelAt(x: number, y: number, rows: number, cols: number): string {
  const row = Math.min(rows - 1, Math.floor(y * rows));
  const col = Math.min(cols - 1, Math.floor(x * cols));
  return `${String.fromCharCode(65 + row)}${col + 1}`;
}

export type Pending = {
  added: Record<string, ElementShape>;
  updated: Record<string, ElementShape>;
  deleted: string[];
};

export const NO_PENDING: Pending = { added: {}, updated: {}, deleted: [] };

export function pendingCount(pending: Pending): number {
  return Object.keys(pending.added).length + Object.keys(pending.updated).length + pending.deleted.length;
}

export function buildEdits(pending: Pending): ElementEdit[] {
  return [
    ...Object.entries(pending.updated).map(
      ([element_id, element]): ElementEdit => ({ action: "update", element_id, element }),
    ),
    ...pending.deleted.map((element_id): ElementEdit => ({ action: "delete", element_id })),
    ...Object.values(pending.added).map((element): ElementEdit => ({ action: "add", element })),
  ];
}

export function withPending(
  elements: MapElement[],
  pending: Pending,
  glossary: Record<string, GlossaryEntry>,
  wall: Wall,
  grid: { rows: number; cols: number },
): MapElement[] {
  const shaped = (id: string, shape: ElementShape): MapElement => {
    const geometry = glossary[shape.damage_type]?.geometry ?? "area";
    const [cx, cy] = centroid(shape.points);
    return {
      id,
      damage_type: shape.damage_type,
      geometry,
      points: shape.points,
      severity: shape.severity as MapElement["severity"],
      confidence: "high",
      source: "expert",
      damage_class: shape.damage_class,
      ...measureShape(geometry, shape.points, wall),
      location: cellLabelAt(cx, cy, grid.rows, grid.cols),
      needs_review: false,
    };
  };
  const kept = elements
    .filter((e) => !pending.deleted.includes(e.id))
    .map((e) => (pending.updated[e.id] ? shaped(e.id, pending.updated[e.id]) : e));
  return [...kept, ...Object.entries(pending.added).map(([id, shape]) => shaped(id, shape))];
}

export function centroid(points: number[][]): [number, number] {
  const x = points.reduce((sum, p) => sum + p[0], 0) / points.length;
  const y = points.reduce((sum, p) => sum + p[1], 0) / points.length;
  return [x, y];
}

function round(value: number): number {
  return Math.round(value * 1000) / 1000;
}
