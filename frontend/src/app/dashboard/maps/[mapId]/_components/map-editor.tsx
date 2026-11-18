"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ApiError } from "@/lib/api";
import { detectorStatusAr, mapStatusAr } from "@/lib/labels";
import { type CellCorrection, type DamageMap, type MapCell, approveMap, correctCells, getMap } from "@/lib/maps";
import { useMe } from "@/lib/use-me";
import { CellInspector } from "./cell-inspector";
import { DamageGrid } from "./damage-grid";
import { DamageLegend } from "./damage-legend";
import { LayerControls, type Layers } from "./layer-controls";
import { MapChangesList } from "./map-changes";
import { type Brush, MapToolbar } from "./map-toolbar";
import { TreatmentPlanView } from "./treatment-plan";

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

  const load = useCallback(
    () => getMap(mapId).then(setMap, (e) => setError(e instanceof ApiError ? e.message : "تعذر تحميل المخطط.")),
    [mapId],
  );

  useEffect(() => {
    if (me) load();
  }, [me, load]);

  const pending = useMemo(() => Object.assign({}, ...strokes) as Stroke, [strokes]);
  const cells = useMemo(() => (map ? withCorrections(map.cells, pending) : []), [map, pending]);
  const canEdit = !!me && me.role !== "inspector" && map?.status === "draft";
  const pendingCount = Object.keys(pending).length;

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
    if (pendingCount === 0) return;
    function warn(event: BeforeUnloadEvent) {
      event.preventDefault();
    }
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [pendingCount]);

  if (error && !map) return <p role="alert" className="pt-6">{error}</p>;
  if (!me || !map) return <EditorSkeleton />;

  async function run(action: () => Promise<DamageMap>) {
    setBusy(true);
    setError(null);
    try {
      setMap(await action());
      setStrokes([]);
      setRedo([]);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "تعذر الحفظ. تصحيحاتك ما زالت هنا، أعد المحاولة.");
    } finally {
      setBusy(false);
    }
  }

  function commitStroke(stroke: Stroke) {
    if (Object.keys(stroke).length === 0) return;
    setStrokes((all) => [...all, stroke]);
    setRedo([]);
  }

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
            <strong className="tabular-nums text-ink">{formatArea(cells.length * map.cell_area_m2)}</strong>
          </p>
          {map.summary_ar && <p className="leading-relaxed">{map.summary_ar}</p>}
        </div>
        <button
          type="button"
          onClick={() => window.print()}
          className="no-print rounded-full border border-ink px-4 py-1.5 text-sm hover:bg-ink hover:text-sand"
        >
          اطبع المخطط وخطة المعالجة
        </button>
      </header>

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

      {error && (
        <p role="alert" className="border-s-4 border-urgent bg-urgent/10 p-3 text-sm">
          {error}
        </p>
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

      {map.changes && <MapChangesList changes={map.changes} />}

      <TreatmentPlanView plan={map.treatment_plan} pendingCount={pendingCount} />
    </div>
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
