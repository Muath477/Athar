"use client";

import { useParams } from "next/navigation";
import { type ReactNode, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { MarginNote } from "@/components/brand/margin-note";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ApiError, can, mapReportUrl } from "@/lib/api";
import { detectorStatusAr, mapStatusAr } from "@/lib/labels";
import { NO_PENDING, buildEdits, pendingCount as countPending, withPending } from "@/lib/elements";
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
import { countAr, unsavedEdits } from "@/lib/plural";
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
import { useElementHistory } from "./use-element-history";
import { WorkflowSteps } from "./workflow-steps";

type Stroke = Record<string, CellCorrection>;
type SaveKind = "elements" | "cells" | "inspect" | "approve";
type Notice = { message: ReactNode; focus: "status" | "elements" };

const SUCCESS_AR: Record<SaveKind, string> = {
  elements: "حُفظت التعديلات في سجل التصحيحات",
  cells: "حُفظت التعديلات في سجل التصحيحات",
  inspect: "سُجّل الفحص الميداني",
  approve: "اعتُمد المخطط والمعالجات",
};

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
  const elementHistory = useElementHistory();
  const pendingElements = elementHistory.pending;
  const { change: changeElements, undo: undoElements, redo: redoElements } = elementHistory;
  const [tool, setTool] = useState<Tool>("select");
  const [drawShape, setDrawShape] = useState<ElementShape>({
    damage_type: "plaster_loss",
    points: [],
    severity: "moderate",
    damage_class: null,
  });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showGrid, setShowGrid] = useState(true);
  const [notice, setNotice] = useState<Notice | null>(null);
  const nextDraftId = useRef(1);
  const statusRef = useRef<HTMLDivElement>(null);

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
  const canEdit = can(me, "review") && map?.status === "draft";
  const pendingCount = Object.keys(pending).length;
  const unsaved = pendingCount + elementEdits;
  const gridLocked = (map?.correction_log.length ?? 0) > 0;

  const undo = useCallback(() => {
    if (strokes.length === 0) return;
    const last = strokes[strokes.length - 1];
    setStrokes(strokes.slice(0, -1));
    setRedo([...redo, last]);
  }, [strokes, redo]);

  const redoLast = useCallback(() => {
    if (redo.length === 0) return;
    const last = redo[redo.length - 1];
    setRedo(redo.slice(0, -1));
    setStrokes([...strokes, last]);
  }, [strokes, redo]);

  useEffect(() => {
    if (!canEdit) return;
    function onKey(event: KeyboardEvent) {
      if (!(event.ctrlKey || event.metaKey) || event.key.toLowerCase() !== "z") return;
      if (isTextEntry(event.target)) return;
      event.preventDefault();
      if (mode === "elements") {
        if (event.shiftKey) redoElements();
        else undoElements();
        return;
      }
      if (event.shiftKey) redoLast();
      else undo();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [canEdit, mode, undo, redoLast, undoElements, redoElements]);

  useEffect(() => {
    if (unsaved === 0) return;
    function warn(event: BeforeUnloadEvent) {
      event.preventDefault();
    }
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [unsaved]);

  useEffect(() => {
    if (unsaved === 0) return;
    function guardLinks(event: MouseEvent) {
      if (event.defaultPrevented || event.button !== 0) return;
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      const anchor = event.target instanceof Element ? event.target.closest("a[href]") : null;
      if (!(anchor instanceof HTMLAnchorElement)) return;
      if (anchor.hasAttribute("download") || (anchor.target && anchor.target !== "_self")) return;
      const destination = new URL(anchor.href, window.location.href);
      if (destination.origin !== window.location.origin) return;
      if (destination.pathname === window.location.pathname && destination.search === window.location.search) return;
      if (window.confirm(`لديك ${countAr(unsaved, unsavedEdits)}. أتترك الصفحة دون حفظ؟`)) return;
      event.preventDefault();
      event.stopPropagation();
    }
    document.addEventListener("click", guardLinks, true);
    return () => document.removeEventListener("click", guardLinks, true);
  }, [unsaved]);

  useEffect(() => {
    if (!notice) return;
    if (notice.focus === "elements") document.getElementById("elements-title")?.focus();
    else statusRef.current?.focus();
    const timer = window.setTimeout(() => setNotice(null), 5000);
    return () => window.clearTimeout(timer);
  }, [notice]);

  if (error && !map) return <p role="alert" className="pt-6">{error}</p>;
  if (!me || !map) return <EditorSkeleton />;

  async function run(kind: SaveKind, action: () => Promise<DamageMap>) {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      setMap(await action());
      if (kind === "cells") {
        setStrokes([]);
        setRedo([]);
      }
      if (kind === "elements") {
        elementHistory.reset();
        setSelectedId(null);
      }
      setNotice({ message: SUCCESS_AR[kind], focus: "status" });
    } catch (e) {
      if (e instanceof ApiError && e.code === "elements_already_edited") {
        setError("عُدّلت عناصر هذا المخطط يدويًا، فلم يعد تعديل الشبكة متاحًا. صحّح من وضع العناصر.");
      } else if (e instanceof ApiError && e.code === "field_inspection_required") {
        setError("سجّل الفحص الميداني للجدار قبل الاعتماد.");
      } else if (e instanceof ApiError && e.code === "low_confidence_unreviewed") {
        setError("في المخطط عناصر بثقة منخفضة. أكّد كل عنصر أو صحّحه أو احذفه قبل الاعتماد.");
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
    const id = `N${nextDraftId.current++}`;
    changeElements((current) => ({ ...current, added: { ...current.added, [id]: { ...drawShape, points } } }));
    setSelectedId(id);
  }

  function changeSelected(shape: ElementShape) {
    if (!selectedId) return;
    changeElements((current) =>
      selectedId in current.added
        ? { ...current, added: { ...current.added, [selectedId]: shape } }
        : { ...current, updated: { ...current.updated, [selectedId]: shape } },
    );
  }

  function deleteSelected() {
    if (!selectedId) return;
    const removedId = selectedId;
    changeElements((current) => {
      if (removedId in current.added) {
        const added = { ...current.added };
        delete added[removedId];
        return { ...current, added };
      }
      const updated = { ...current.updated };
      delete updated[removedId];
      return { ...current, updated, deleted: [...current.deleted, removedId] };
    });
    setSelectedId(null);
    setNotice({
      message: (
        <>
          حُذف العنصر <bdi>{removedId}</bdi>. يمكنك التراجع عن حذفه قبل الحفظ.
        </>
      ),
      focus: "elements",
    });
  }

  const selected = shownElements.find((e) => e.id === selectedId) ?? null;
  const focused = focusCell ? (cells.find((c) => c.cell === focusCell) ?? null) : null;
  const change = focusCell ? (map.changes?.items.find((c) => c.cell === focusCell) ?? null) : null;

  return (
    <div className="flex flex-col gap-5">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex max-w-prose flex-col gap-1.5">
          <p className="flex flex-wrap items-center gap-2 text-sm text-mud">
            <Badge variant={map.status === "approved" ? "ink" : "outline"}>{mapStatusAr[map.status]}</Badge>
            {unsaved > 0 && <Badge variant="watch">تعديلات غير محفوظة: {unsaved.toLocaleString("ar-SA")}</Badge>}
            <span>
              {detectorStatusAr[map.detector_status]} · {new Date(map.created_at).toLocaleDateString("ar-SA")}
            </span>
          </p>
          <h1 className="text-3xl font-bold">{map.wall_name}</h1>
          <p className="text-mud">
            <bdi className="tabular-nums">{formatMeters(map.width_m)}</bdi> عرضًا ×{" "}
            <bdi className="tabular-nums">{formatMeters(map.height_m)}</bdi> ارتفاعًا ·{" "}
            {map.damaged_area_m2 > 0 ? (
              <>
                المتضرر <strong className="tabular-nums text-ink">{formatArea(map.damaged_area_m2)}</strong>
              </>
            ) : (
              "لا تلف محدد بعد"
            )}
          </p>
          {map.summary_ar && (
            <MarginNote label="حاشية التحليل" className="mt-1">
              {map.summary_ar}
            </MarginNote>
          )}
        </div>
        <div className="no-print flex flex-col items-start gap-1">
          <a
            href={mapReportUrl(map.id)}
            download
            className={buttonVariants({ variant: map.status === "approved" ? "default" : "outline" })}
          >
            حمّل التقرير PDF
          </a>
          {unsaved > 0 && <p className="text-xs text-mud">احفظ تصحيحاتك أولًا ليتضمنها التقرير.</p>}
        </div>
      </header>

      <WorkflowSteps steps={map.workflow} />

      <Tabs value={mode} onValueChange={(value) => setMode(value as typeof mode)}>
        <TabsList aria-label="طريقة العرض" className="no-print">
          <TabsTrigger value="elements">عناصر التلف بالمسرد</TabsTrigger>
          <TabsTrigger value="grid">شبكة النموذج</TabsTrigger>
        </TabsList>

        <div className="flex flex-col gap-3">
          {error && (
            <p role="alert" className="rounded-sm border border-urgent/40 bg-urgent/5 p-3 text-sm">
              {error}
            </p>
          )}
          <div ref={statusRef} role="status" tabIndex={-1} className="no-print">
            {notice && <p className="rounded-sm border border-line bg-white p-3 text-sm">{notice.message}</p>}
          </div>
        </div>

        <TabsContent value="elements">
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
              canUndo={elementHistory.canUndo}
              canRedo={elementHistory.canRedo}
              onUndo={undoElements}
              onRedo={redoElements}
              onSave={() => run("elements", () => editElements(map.id, buildEdits(pendingElements)))}
              onDiscard={() => {
                changeElements(() => NO_PENDING);
                setSelectedId(null);
              }}
            />
          )}
          <div className="grid gap-5 lg:grid-cols-[minmax(0,3fr)_minmax(16rem,1fr)]">
            <div className="flex flex-col gap-3">
              <div className="no-print flex min-h-11 w-fit items-center gap-2">
                <Checkbox id="show-grid" checked={showGrid} onCheckedChange={(checked) => setShowGrid(checked === true)} />
                <Label htmlFor="show-grid" className="text-ink">
                  أظهر الشبكة المرجعية
                </Label>
              </div>
              <ElementCanvas
                map={map}
                elements={shownElements}
                glossary={glossaryByType}
                tool={canEdit ? tool : "select"}
                draftKey={`${canEdit ? tool : "select"}-${drawShape.damage_type}`}
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
                onInspect={(notes) => run("inspect", () => recordFieldInspection(map.id, notes))}
                onApprove={() => run("approve", () => approveMap(map.id))}
              />
            </div>
          </div>
        </TabsContent>

        <TabsContent value="grid">
          {canEdit && gridLocked && (
            <p className="no-print rounded-lg bg-white/75 p-3 text-sm">
              عُدّلت عناصر هذا المخطط يدويًا، فالشبكة الآن للعرض فقط. التصحيح من وضع «عناصر التلف بالمسرد».
            </p>
          )}
          {canEdit && !gridLocked && (
            <MapToolbar
              damageTypes={map.damage_types}
              brush={brush}
              onBrush={setBrush}
              pendingCount={pendingCount}
              unsaved={unsaved}
              fieldInspected={!!map.field_inspected_at}
              unreviewed={shownElements.filter((e) => e.needs_review).length}
              canUndo={strokes.length > 0}
              canRedo={redo.length > 0}
              busy={busy}
              onUndo={undo}
              onRedo={redoLast}
              onSave={() => run("cells", () => correctCells(map.id, Object.values(pending)))}
              onApprove={() => run("approve", () => approveMap(map.id))}
            />
          )}

          <div className="grid gap-5 lg:grid-cols-[minmax(0,3fr)_minmax(16rem,1fr)]">
            <div className="flex flex-col gap-2">
              <LayerControls layers={layers} onChange={setLayers} hasChanges={!!map.changes?.items.length} />
              <DamageGrid
                map={map}
                cells={cells}
                layers={layers}
                brush={canEdit && !gridLocked ? brush : null}
                focusCell={focusCell}
                onFocusCell={setFocusCell}
                onStroke={commitStroke}
              />
              <CellInspector label={focusCell} cell={focused} change={change} editable={canEdit && !gridLocked} />
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
        </TabsContent>
      </Tabs>

      {map.changes && <MapChangesList changes={map.changes} />}

      <TreatmentPlanView plan={map.treatment_plan} pendingCount={unsaved} />
    </div>
  );
}

function GlossaryLegend({ glossary }: { glossary: GlossaryEntry[] }) {
  return (
    <section aria-labelledby="glossary-title" className="flex flex-col gap-2">
      <h2 id="glossary-title" className="font-bold">
        المسرد الموحد
      </h2>
      <ul className="flex flex-col gap-1.5 text-sm">
        {glossary
          .filter((g) => g.core)
          .map((g) => (
            <li key={g.damage_type} className="flex items-start gap-2">
              <span
                className="mt-1.5 inline-block size-3.5 shrink-0 rounded-xs border border-ink/30"
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

function isTextEntry(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName);
}

function formatMeters(value: number): string {
  return `${value.toLocaleString("ar-SA", { maximumFractionDigits: 1 })} م`;
}

function formatArea(value: number): string {
  return `${value.toLocaleString("ar-SA", { maximumFractionDigits: 1 })} م²`;
}

function EditorSkeleton() {
  return (
    <div role="status" aria-busy="true" aria-label="جارٍ تحميل المخطط" className="flex flex-col gap-5">
      <Skeleton className="h-9 w-64" />
      <div className="grid gap-5 lg:grid-cols-[3fr_1fr]">
        <Skeleton className="aspect-[16/10]" />
        <Skeleton className="h-64" />
      </div>
    </div>
  );
}
