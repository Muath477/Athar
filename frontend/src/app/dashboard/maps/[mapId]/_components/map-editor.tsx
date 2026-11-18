"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ApiError, mapReportUrl } from "@/lib/api";
import { detectorStatusAr, mapStatusAr } from "@/lib/labels";
import { NO_PENDING, type Pending, buildEdits, pendingCount as countPending, withPending } from "@/lib/elements";
import {
  type CellCorrection,
  type DamageMap,
  type ElementShape,
  type GlossaryEntry,
  type MapCell,
  approveMap,
  correctCells,
  editElements,
  getGlossary,
  getMap,
  recordFieldInspection,
} from "@/lib/maps";
import { useMe } from "@/lib/use-me";
import { CellInspector } from "./cell-inspector";
import { DamageGrid } from "./damage-grid";
import { DamageLegend } from "./damage-legend";
import { ElementCanvas, type Tool } from "./element-canvas";
import { ElementList } from "./element-list";
import { ElementTools } from "./element-tools";
import { FieldReview } from "./field-review";
import { LayerControls, type Layers } from "./layer-controls";
import { MapChangesList } from "./map-changes";
import { type Brush, MapToolbar } from "./map-toolbar";
import { TreatmentPlanView } from "./treatment-plan";
import { WorkflowSteps } from "./workflow-steps";

type Stroke = Record<string, CellCorrection>;

export function MapEditor() {
  const { mapId } = useParams<{ mapId: string }>();
  const me = useMe();
  const [map, setMap] = useState<DamageMap | null>(null);
  const [strokes, setStrokes] = useState<Stroke[]>([]);
  const [redo, setRedo] = useState<Stroke[]>([]);
  const [brush, setBrush] = useState<Brush>({ damage_type: "crack", severity: "moderate" });
  const [layers, setLayers] = useState<Layers>({ opacity: 1, grid: true, changes: false, hidden: [] });
  const [focusCell, setFocusCell] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<"elements" | "grid">("elements");
  const [glossary, setGlossary] = useState<GlossaryEntry[]>([]);
  const [pendingElements, setPendingElements] = useState<Pending>(NO_PENDING);
  const [tool, setTool] = useState<Tool>("select");
  const [drawShape, setDrawShape] = useState<ElementShape>({
    damage_type: "plaster_loss",
    points: [],
    severity: "moderate",
    damage_class: null,
  });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showGrid, setShowGrid] = useState(true);

  const load = useCallback(
    () => getMap(mapId).then(setMap, (e) => setError(e instanceof ApiError ? e.message : "تعذر تحميل المخطط.")),
    [mapId],
  );

  useEffect(() => {
    if (me) load();
  }, [me, load]);

  useEffect(() => {
    if (me) getGlossary().then(setGlossary, () => setGlossary([]));
  }, [me]);

  const glossaryByType = useMemo(() => Object.fromEntries(glossary.map((g) => [g.damage_type, g])), [glossary]);
  const shownElements = useMemo(
    () =>
      map
        ? withPending(map.elements, pendingElements, glossaryByType, map, { rows: map.rows, cols: map.cols })
        : [],
    [map, pendingElements, glossaryByType],
  );
  const elementEdits = countPending(pendingElements);

  const pending = useMemo(() => Object.assign({}, ...strokes) as Stroke, [strokes]);
  const cells = useMemo(() => (map ? withCorrections(map.cells, pending) : []), [map, pending]);
  const canEdit = !!me && me.role !== "inspector" && map?.status === "draft";
  const pendingCount = Object.keys(pending).length;
  const unsaved = pendingCount + elementEdits;

  const undo = useCallback(() => {
    setStrokes((all) => {
      if (all.length === 0) return all;
      setRedo((r) => [...r, all[all.length - 1]]);
      return all.slice(0, -1);
    });
  }, []);

  const redoLast = useCallback(() => {
    setRedo((all) => {
      if (all.length === 0) return all;
      setStrokes((s) => [...s, all[all.length - 1]]);
      return all.slice(0, -1);
    });
  }, []);

  useEffect(() => {
    if (!canEdit) return;
    function onKey(event: KeyboardEvent) {
      if (!(event.ctrlKey || event.metaKey) || event.key.toLowerCase() !== "z") return;
      event.preventDefault();
      if (event.shiftKey) redoLast();
      else undo();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [canEdit, undo, redoLast]);

  useEffect(() => {
    if (unsaved === 0) return;
    function warn(event: BeforeUnloadEvent) {
      event.preventDefault();
    }
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [unsaved]);

  if (error && !map) return <p role="alert" className="pt-6">{error}</p>;
  if (!me || !map) return <EditorSkeleton />;

  async function run(action: () => Promise<DamageMap>) {
    setBusy(true);
    setError(null);
    try {
      setMap(await action());
      setStrokes([]);
      setRedo([]);
      setPendingElements(NO_PENDING);
      setSelectedId(null);
    } catch (e) {
      if (e instanceof ApiError && e.code === "field_inspection_required") {
        setError("سجّل الفحص الميداني للجدار قبل الاعتماد.");
      } else if (e instanceof ApiError && e.code === "low_confidence_unreviewed") {
        setError("في الخريطة عناصر بثقة منخفضة. أكّد كل عنصر أو صحّحه أو احذفه قبل الاعتماد.");
      } else {
        setError(e instanceof ApiError ? e.message : "تعذر الحفظ. تصحيحاتك ما زالت هنا، أعد المحاولة.");
      }
    } finally {
      setBusy(false);
    }
  }

  function commitStroke(stroke: Stroke) {
    if (Object.keys(stroke).length === 0) return;
    setStrokes((all) => [...all, stroke]);
    setRedo([]);
  }

  function addElement(points: number[][]) {
    const id = `N${Object.keys(pendingElements.added).length + 1}`;
    setPendingElements((current) => ({ ...current, added: { ...current.added, [id]: { ...drawShape, points } } }));
    setSelectedId(id);
  }

  function changeSelected(shape: ElementShape) {
    if (!selectedId) return;
    setPendingElements((current) =>
      selectedId in current.added
        ? { ...current, added: { ...current.added, [selectedId]: shape } }
        : { ...current, updated: { ...current.updated, [selectedId]: shape } },
    );
  }

  function deleteSelected() {
    if (!selectedId) return;
    setPendingElements((current) => {
      if (selectedId in current.added) {
        const added = { ...current.added };
        delete added[selectedId];
        return { ...current, added };
      }
      const updated = { ...current.updated };
      delete updated[selectedId];
      return { ...current, updated, deleted: [...current.deleted, selectedId] };
    });
    setSelectedId(null);
  }

  const selected = shownElements.find((e) => e.id === selectedId) ?? null;
  const focused = focusCell ? (cells.find((c) => c.cell === focusCell) ?? null) : null;
  const change = focusCell ? (map.changes?.items.find((c) => c.cell === focusCell) ?? null) : null;

  return (
    <div className="flex flex-col gap-5">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex max-w-prose flex-col gap-1.5">
          <p className="text-sm text-mud">
            <span
              className={`me-2 rounded-full px-2.5 py-0.5 text-xs font-bold ${
                map.status === "approved" ? "bg-ink text-sand" : "bg-white/80 text-ink"
              }`}
            >
              {mapStatusAr[map.status]}
            </span>
            {detectorStatusAr[map.detector_status]} · {new Date(map.created_at).toLocaleDateString("ar-SA")}
          </p>
          <h1 className="text-3xl font-bold leading-tight">{map.wall_name}</h1>
          <p className="text-mud">
            <bdi className="tabular-nums">{formatMeters(map.width_m)}</bdi> عرضًا ×{" "}
            <bdi className="tabular-nums">{formatMeters(map.height_m)}</bdi> ارتفاعًا · المتضرر{" "}
            <strong className="tabular-nums text-ink">{formatArea(map.damaged_area_m2)}</strong>
          </p>
          {map.summary_ar && <p className="leading-relaxed">{map.summary_ar}</p>}
        </div>
        <div className="no-print flex flex-col items-start gap-1">
          <a
            href={mapReportUrl(map.id)}
            download
            className="min-h-11 content-center rounded-full bg-sadu px-5 text-sm font-bold text-sand hover:bg-ink"
          >
            حمّل التقرير PDF
          </a>
          {unsaved > 0 && <p className="text-xs text-mud">احفظ تصحيحاتك أولًا ليتضمنها التقرير.</p>}
        </div>
      </header>

      <WorkflowSteps steps={map.workflow} />

      <div role="group" aria-label="طريقة العرض" className="no-print flex w-fit gap-1 rounded-full bg-white/60 p-1">
        {(
          [
            ["elements", "عناصر التلف بالمسرد"],
            ["grid", "شبكة النموذج"],
          ] as const
        ).map(([value, label]) => (
          <button
            key={value}
            type="button"
            aria-pressed={mode === value}
            onClick={() => setMode(value)}
            className={`min-h-9 rounded-full px-4 text-sm ${mode === value ? "bg-ink text-sand" : "hover:bg-clay/20"}`}
          >
            {label}
          </button>
        ))}
      </div>

      {error && (
        <p role="alert" className="border-s-4 border-urgent bg-urgent/10 p-3 text-sm">
          {error}
        </p>
      )}

      {mode === "elements" ? (
        <>
          {canEdit && glossary.length > 0 && (
            <ElementTools
              glossary={glossary}
              tool={tool}
              onTool={setTool}
              draft={drawShape}
              onDraft={setDrawShape}
              selected={selected}
              onChangeSelected={changeSelected}
              onDeleteSelected={deleteSelected}
              pendingCount={elementEdits}
              busy={busy}
              onSave={() => run(() => editElements(map.id, buildEdits(pendingElements)))}
              onDiscard={() => {
                setPendingElements(NO_PENDING);
                setSelectedId(null);
              }}
            />
          )}
          <div className="grid gap-5 lg:grid-cols-[minmax(0,3fr)_minmax(16rem,1fr)]">
            <div className="flex flex-col gap-3">
              <label className="no-print flex w-fit items-center gap-2 text-sm">
                <input type="checkbox" checked={showGrid} onChange={(e) => setShowGrid(e.target.checked)} />
                أظهر الشبكة المرجعية
              </label>
              <ElementCanvas
                map={map}
                elements={shownElements}
                glossary={glossaryByType}
                tool={canEdit ? tool : "select"}
                drawColor={glossaryByType[drawShape.damage_type]?.color ?? "#555"}
                selectedId={selectedId}
                showGrid={showGrid}
                onSelect={setSelectedId}
                onDraw={addElement}
              />
              <ElementList
                elements={shownElements}
                glossary={glossaryByType}
                selectedId={selectedId}
                onSelect={setSelectedId}
              />
            </div>
            <div className="flex flex-col gap-4">
              <GlossaryLegend glossary={glossary} />
              <FieldReview
                map={map}
                canReview={canEdit}
                busy={busy}
                pendingCount={unsaved}
                unreviewed={shownElements.filter((e) => e.needs_review).length}
                onInspect={(notes) => run(() => recordFieldInspection(map.id, notes))}
                onApprove={() => run(() => approveMap(map.id))}
              />
            </div>
          </div>
        </>
      ) : (
        <>
      {canEdit && (
        <MapToolbar
          damageTypes={map.damage_types}
          brush={brush}
          onBrush={setBrush}
          pendingCount={pendingCount}
          canUndo={strokes.length > 0}
          canRedo={redo.length > 0}
          busy={busy}
          onUndo={undo}
          onRedo={redoLast}
          onSave={() => run(() => correctCells(map.id, Object.values(pending)))}
          onApprove={() => run(() => approveMap(map.id))}
        />
      )}

      <div className="grid gap-5 lg:grid-cols-[minmax(0,3fr)_minmax(16rem,1fr)]">
        <div className="flex flex-col gap-2">
          <LayerControls layers={layers} onChange={setLayers} hasChanges={!!map.changes?.items.length} />
          <DamageGrid
            map={map}
            cells={cells}
            layers={layers}
            brush={canEdit ? brush : null}
            focusCell={focusCell}
            onFocusCell={setFocusCell}
            onStroke={commitStroke}
          />
          <CellInspector label={focusCell} cell={focused} change={change} editable={canEdit} />
        </div>
        <DamageLegend
          map={map}
          cells={cells}
          hidden={layers.hidden}
          onToggle={(type) =>
            setLayers((current) => ({
              ...current,
              hidden: current.hidden.includes(type)
                ? current.hidden.filter((t) => t !== type)
                : [...current.hidden, type],
            }))
          }
        />
      </div>

        </>
      )}

      {map.changes && <MapChangesList changes={map.changes} />}

      <TreatmentPlanView plan={map.treatment_plan} pendingCount={unsaved} />
    </div>
  );
}

function GlossaryLegend({ glossary }: { glossary: GlossaryEntry[] }) {
  return (
    <section aria-labelledby="glossary-title" className="flex flex-col gap-2 rounded-xl bg-white/75 p-3">
      <h2 id="glossary-title" className="font-bold">
        المسرد الموحد
      </h2>
      <ul className="flex flex-col gap-1.5 text-sm">
        {glossary
          .filter((g) => g.core)
          .map((g) => (
            <li key={g.damage_type} className="flex items-start gap-2">
              <span
                className="mt-1 inline-block size-3.5 shrink-0 rounded-sm border border-ink/30"
                style={{ background: g.color }}
              />
              <span>
                <span className="font-bold">{g.name_ar}</span>
                <span className="block text-xs text-mud">{g.measure_ar}</span>
              </span>
            </li>
          ))}
      </ul>
    </section>
  );
}

function withCorrections(cells: MapCell[], pending: Record<string, CellCorrection>): MapCell[] {
  const byCell = new Map(cells.map((c) => [c.cell, c]));
  for (const correction of Object.values(pending)) {
    if (correction.damage_type === "none") {
      byCell.delete(correction.cell);
      continue;
    }
    byCell.set(correction.cell, {
      cell: correction.cell,
      row: correction.cell.charCodeAt(0) - 65,
      col: Number(correction.cell.slice(1)) - 1,
      damage_type: correction.damage_type,
      severity: correction.severity as MapCell["severity"],
      confidence: "high",
      source: "expert",
    });
  }
  return [...byCell.values()];
}

function formatMeters(value: number): string {
  return `${value.toLocaleString("ar-SA", { maximumFractionDigits: 1 })} م`;
}

function formatArea(value: number): string {
  return `${value.toLocaleString("ar-SA", { maximumFractionDigits: 1 })} م²`;
}

function EditorSkeleton() {
  return (
    <div aria-busy="true" aria-label="جارٍ تحميل المخطط" className="flex flex-col gap-5">
      <div className="h-9 w-64 animate-pulse rounded bg-clay/25" />
      <div className="grid gap-5 lg:grid-cols-[3fr_1fr]">
        <div className="aspect-[16/10] animate-pulse rounded-xl bg-clay/20" />
        <div className="h-64 animate-pulse rounded-xl bg-clay/15" />
      </div>
    </div>
  );
}
