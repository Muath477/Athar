"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ApiError } from "@/lib/api";
import { damageTypeAr, detectorStatusAr, mapStatusAr } from "@/lib/labels";
import { type CellCorrection, type DamageMap, type MapCell, approveMap, correctCells, getMap } from "@/lib/maps";
import { useMe } from "@/lib/use-me";
import { CellEditor } from "./cell-editor";
import { DamageGrid } from "./damage-grid";
import { DamageLegend } from "./damage-legend";
import { MapChangesList } from "./map-changes";
import { TreatmentPlanView } from "./treatment-plan";

export function MapEditor() {
  const { mapId } = useParams<{ mapId: string }>();
  const me = useMe();
  const [map, setMap] = useState<DamageMap | null>(null);
  const [pending, setPending] = useState<Record<string, CellCorrection>>({});
  const [selected, setSelected] = useState<string | null>(null);
  const [showChanges, setShowChanges] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    () => getMap(mapId).then(setMap, (e) => setError(e instanceof ApiError ? e.message : "تعذر تحميل المخطط.")),
    [mapId],
  );

  useEffect(() => {
    if (me) load();
  }, [me, load]);

  const cells = useMemo(() => (map ? withCorrections(map.cells, pending) : []), [map, pending]);

  if (!me || !map) return <p className="pt-6">{error ?? "…"}</p>;

  const canEdit = me.role !== "inspector" && map.status === "draft";
  const pendingCount = Object.keys(pending).length;

  async function run(action: () => Promise<DamageMap>) {
    setBusy(true);
    setError(null);
    try {
      setMap(await action());
      setPending({});
      setSelected(null);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "تعذر حفظ التغييرات.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-5 pt-2">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-bold">{map.wall_name}</h1>
          <p className="text-sm">
            {mapStatusAr[map.status]} · {detectorStatusAr[map.detector_status]} ·{" "}
            {new Date(map.created_at).toLocaleDateString("ar-SA")} · {formatMeters(map.width_m)} ×{" "}
            {formatMeters(map.height_m)}
          </p>
          {map.summary_ar && <p className="leading-relaxed">{map.summary_ar}</p>}
        </div>
        <div className="no-print flex flex-wrap gap-2">
          {map.changes && (
            <button
              type="button"
              onClick={() => setShowChanges((v) => !v)}
              aria-pressed={showChanges}
              className="rounded-full border border-ink px-4 py-1.5"
            >
              {showChanges ? "إخفاء التغييرات" : "إظهار التغييرات"}
            </button>
          )}
          <button type="button" onClick={() => window.print()} className="rounded-full border border-ink px-4 py-1.5">
            طباعة / PDF
          </button>
        </div>
      </header>

      {error && (
        <p role="alert" className="rounded-lg bg-urgent/10 p-2 text-urgent">
          {error}
        </p>
      )}

      <div className="grid gap-4 lg:grid-cols-[3fr_1fr]">
        <DamageGrid
          map={map}
          cells={cells}
          selected={selected}
          changes={showChanges ? map.changes : null}
          onSelect={canEdit ? setSelected : undefined}
        />
        <div className="flex flex-col gap-4">
          {canEdit && selected && (
            <CellEditor
              key={selected}
              cell={selected}
              current={cells.find((c) => c.cell === selected) ?? null}
              damageTypes={map.damage_types}
              onApply={(correction) => {
                setPending((all) => ({ ...all, [correction.cell]: correction }));
                setSelected(null);
              }}
              onCancel={() => setSelected(null)}
            />
          )}
          <DamageLegend map={map} cells={cells} />
        </div>
      </div>

      {canEdit && (
        <div className="no-print flex flex-wrap items-center gap-3 rounded-xl bg-white/60 p-3">
          <p className="text-sm">
            {pendingCount > 0
              ? `${pendingCount.toLocaleString("ar-SA")} تصحيح لم يُحفظ بعد.`
              : "اضغط على أي خلية لتصحيح نوع التلف أو خطورته."}
          </p>
          <button
            type="button"
            disabled={busy || pendingCount === 0}
            onClick={() => run(() => correctCells(map.id, Object.values(pending)))}
            className="rounded-full bg-ink px-4 py-1.5 text-sand disabled:opacity-50"
          >
            حفظ التصحيحات
          </button>
          <button
            type="button"
            disabled={busy || pendingCount > 0}
            onClick={() => run(() => approveMap(map.id))}
            className="rounded-full bg-sadu px-4 py-1.5 font-bold text-sand disabled:opacity-50"
          >
            اعتماد المخطط
          </button>
        </div>
      )}

      {map.changes && <MapChangesList changes={map.changes} />}

      <TreatmentPlanView plan={map.treatment_plan} />

      <p className="text-xs">
        أنواع التلف في هذا المخطط: {map.damage_types.map((t) => damageTypeAr[t] ?? t).join("، ")}.
      </p>
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
    const [row, col] = parseCell(correction.cell);
    byCell.set(correction.cell, {
      cell: correction.cell,
      row,
      col,
      damage_type: correction.damage_type,
      severity: correction.severity as MapCell["severity"],
      confidence: "high",
      source: "expert",
    });
  }
  return [...byCell.values()];
}

function parseCell(label: string): [number, number] {
  return [label.charCodeAt(0) - 65, Number(label.slice(1)) - 1];
}

function formatMeters(value: number): string {
  return `${value.toLocaleString("ar-SA", { maximumFractionDigits: 1 })} م`;
}
