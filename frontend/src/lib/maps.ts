import { request } from "@/lib/api";

export type MapCell = {
  cell: string;
  row: number;
  col: number;
  damage_type: string;
  severity: "watch" | "moderate" | "urgent";
  confidence: "low" | "medium" | "high";
  source: "model" | "expert";
};

export type PlanItem = {
  code: string;
  title_ar: string;
  damage_type: string;
  severity: string;
  area_m2: number;
  cells: number;
  steps_ar: string[];
  tools_ar: string[];
  materials: { name_ar: string; unit_ar: string; quantity: number }[];
  specialist_required: boolean;
  sources: { title: string; url: string }[];
  locations: string[];
};

export type TreatmentPlan = {
  catalog_version: string;
  review_status: "draft" | "approved";
  quantities_note_ar: string;
  needs_specialist: boolean;
  items: PlanItem[];
  unmatched: { damage_type: string; severity: string; area_m2: number; cells: number }[];
};

export type MapChange = {
  cell: string;
  kind: "new" | "worse" | "retyped" | "improved" | "resolved";
  before_type: string | null;
  before_severity: string | null;
  after_type: string | null;
  after_severity: string | null;
};

export type MapChanges = {
  previous_map_id: string;
  previous_created_at: string;
  comparable: boolean;
  items: MapChange[];
};

export type DamageMap = {
  id: string;
  site_id: string | null;
  facade_id: string | null;
  wall_name: string;
  width_m: number;
  height_m: number;
  rows: number;
  cols: number;
  cell_area_m2: number;
  corners: number[][];
  photo_url: string;
  rectified_url: string;
  rectified_width_px: number;
  rectified_height_px: number;
  detector: string;
  detector_status: "ok" | "failed" | "manual";
  summary_ar: string;
  status: "draft" | "approved";
  created_at: string;
  approved_at: string | null;
  damaged_area_m2: number;
  damage_types: string[];
  cells: MapCell[];
  elements: MapElement[];
  workflow: WorkflowStep[];
  correction_log: CorrectionLogEntry[];
  field_inspected_at: string | null;
  field_notes: string;
  treatment_plan: TreatmentPlan;
  changes: MapChanges | null;
};

export type Geometry = "area" | "line" | "point";

export type MapElement = {
  id: string;
  damage_type: string;
  geometry: Geometry;
  points: number[][];
  severity: "watch" | "moderate" | "urgent";
  confidence: "low" | "medium" | "high";
  source: "model" | "expert";
  damage_class: string | null;
  area_m2: number;
  length_m: number;
  count: number;
  location: string;
  needs_review: boolean;
};

export type GlossaryEntry = {
  damage_type: string;
  name_ar: string;
  geometry: Geometry;
  measure_ar: string;
  class_kind: "width" | "depth" | "size" | null;
  classes: string[];
  color: string;
  core: boolean;
};

export type WorkflowStep = {
  number: number;
  key: string;
  title_ar: string;
  actor: "agent" | "specialist";
  criterion: "none" | "privacy" | "accuracy" | "reviewability" | "map_clarity";
  state: "done" | "flagged" | "waiting" | "blocked";
  output_ar: string;
};

export type CorrectionLogEntry = {
  at: string;
  by: string;
  action: "add" | "update" | "delete";
  element_id: string;
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
};

export type ElementShape = {
  damage_type: string;
  points: number[][];
  severity: string;
  damage_class: string | null;
};

export type ElementEdit =
  | { action: "add"; element: ElementShape }
  | { action: "update"; element_id: string; element: ElementShape }
  | { action: "delete"; element_id: string };

export type MapSummary = {
  id: string;
  site_id: string | null;
  facade_id: string | null;
  wall_name: string;
  status: "draft" | "approved";
  detector_status: "ok" | "failed" | "manual";
  damaged_cells: number;
  urgent_cells: number;
  total_cells: number;
  thumbnail_url: string;
  created_at: string;
};

export type TypeScore = {
  damage_type: string;
  true_positives: number;
  false_positives: number;
  false_negatives: number;
  precision: number | null;
  recall: number | null;
  f1: number | null;
};

export type MapAccuracy = {
  maps: number;
  cells: number;
  damaged_vs_sound_accuracy: number | null;
  by_type: TypeScore[];
};

export type NewMapMeta = {
  facade_id?: string;
  wall_name?: string;
  width_m?: number;
  height_m?: number;
  corners?: number[][];
};

export type CellCorrection = { cell: string; damage_type: string; severity: string };

export function listMaps(): Promise<MapSummary[]> {
  return request<MapSummary[]>("/maps");
}

export function getMap(mapId: string): Promise<DamageMap> {
  return request<DamageMap>(`/maps/${mapId}`);
}

export function getAccuracy(): Promise<MapAccuracy> {
  return request<MapAccuracy>("/maps/accuracy");
}

export function createMap(photo: File, meta: NewMapMeta): Promise<DamageMap> {
  const body = new FormData();
  body.append("photo", photo);
  body.append("meta", JSON.stringify(meta));
  return request<DamageMap>("/maps", { method: "POST", body });
}

export function correctCells(mapId: string, corrections: CellCorrection[]): Promise<DamageMap> {
  return request<DamageMap>(`/maps/${mapId}/cells`, { method: "POST", body: JSON.stringify({ corrections }) });
}

export function approveMap(mapId: string): Promise<DamageMap> {
  return request<DamageMap>(`/maps/${mapId}/approve`, { method: "POST" });
}

export function cellLabel(row: number, col: number): string {
  return `${String.fromCharCode(65 + row)}${col + 1}`;
}

export function getGlossary(): Promise<GlossaryEntry[]> {
  return request<GlossaryEntry[]>("/maps/glossary");
}

export function editElements(mapId: string, edits: ElementEdit[]): Promise<DamageMap> {
  return request<DamageMap>(`/maps/${mapId}/elements`, { method: "POST", body: JSON.stringify({ edits }) });
}

export function recordFieldInspection(mapId: string, notes: string): Promise<DamageMap> {
  return request<DamageMap>(`/maps/${mapId}/field-inspection`, { method: "POST", body: JSON.stringify({ notes }) });
}

export type WallCondition = {
  name_ar: string;
  facade_id: string | null;
  map_id: string | null;
  status: "draft" | "approved" | "not_surveyed";
  surveyed_at: string | null;
  approved_at: string | null;
  field_inspected_at: string | null;
  elements: number;
  urgent: number;
  needs_review: number;
  damaged_area_m2: number;
  needs_specialist: boolean;
  survey_due: boolean;
};

export type SiteCondition = {
  site_id: string;
  name_ar: string;
  building_type: string;
  field_photography_permitted: boolean;
  generated_at: string;
  urgent: number;
  walls_due: number;
  awaiting_approval: number;
  catalog_reviewed: boolean;
  walls: WallCondition[];
  totals: { damage_type: string; elements: number; area_m2: number; urgent: number }[];
  materials: { name_ar: string; unit_ar: string; quantity: number }[];
};

export function getSiteCondition(siteId: string): Promise<SiteCondition> {
  return request<SiteCondition>(`/sites/${siteId}/condition`);
}

export function setFieldPhotography(siteId: string, permitted: boolean): Promise<unknown> {
  return request(`/sites/${siteId}/field-photography`, { method: "POST", body: JSON.stringify({ permitted }) });
}
