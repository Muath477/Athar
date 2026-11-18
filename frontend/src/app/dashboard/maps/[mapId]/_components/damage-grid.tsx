"use client";

import { type KeyboardEvent, useEffect, useRef, useState } from "react";
import { colorFor, severityOpacity } from "@/lib/damage-palette";
import type { CellCorrection, DamageMap, MapCell } from "@/lib/maps";
import { cellLabel } from "@/lib/maps";
import type { Layers } from "./layer-controls";
import type { Brush } from "./map-toolbar";

type Stroke = Record<string, CellCorrection>;

export function DamageGrid({
  map,
  cells,
  layers,
  brush,
  focusCell,
  onFocusCell,
  onStroke,
}: {
  map: DamageMap;
  cells: MapCell[];
  layers: Layers;
  brush: Brush | null;
  focusCell: string | null;
  onFocusCell: (cell: string | null) => void;
  onStroke: (stroke: Stroke) => void;
}) {
  const stroke = useRef<Stroke>({});
  const [live, setLive] = useState<Stroke>({});
  const [painting, setPainting] = useState(false);

  useEffect(() => {
    if (!painting) return;
    function finish() {
      onStroke(stroke.current);
      stroke.current = {};
      setLive({});
      setPainting(false);
    }
    window.addEventListener("pointerup", finish);
    window.addEventListener("pointercancel", finish);
    return () => {
      window.removeEventListener("pointerup", finish);
      window.removeEventListener("pointercancel", finish);
    };
  }, [painting, onStroke]);

  function paint(label: string) {
    if (!brush || stroke.current[label]) return;
    stroke.current = { ...stroke.current, [label]: { cell: label, ...brush } };
    setLive(stroke.current);
  }

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    const current = focusCell ?? "A1";
    let row = current.charCodeAt(0) - 65;
    let col = Number(current.slice(1)) - 1;
    const moves: Record<string, () => void> = {
      ArrowUp: () => (row = Math.max(0, row - 1)),
      ArrowDown: () => (row = Math.min(map.rows - 1, row + 1)),
      ArrowLeft: () => (col = Math.max(0, col - 1)),
      ArrowRight: () => (col = Math.min(map.cols - 1, col + 1)),
    };
    if (moves[event.key]) {
      event.preventDefault();
      moves[event.key]();
      onFocusCell(cellLabel(row, col));
      return;
    }
    if ((event.key === " " || event.key === "Enter") && brush) {
      event.preventDefault();
      onStroke({ [current]: { cell: current, ...brush } });
      onFocusCell(current);
    }
  }

  const byCell = new Map(cells.map((c) => [c.cell, c]));
  for (const correction of Object.values(live)) {
    if (correction.damage_type === "none") byCell.delete(correction.cell);
    else
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
  const changed = new Set(layers.changes ? (map.changes?.items ?? []).map((c) => c.cell) : []);
  const labels = Array.from({ length: map.rows * map.cols }, (_, i) => cellLabel(Math.floor(i / map.cols), i % map.cols));

  return (
    <figure className="flex flex-col gap-2">
      <div
        dir="ltr"
        tabIndex={0}
        role="application"
        aria-label={`شبكة التلف ${map.rows} صفوف في ${map.cols} أعمدة. تنقّل بالأسهم${brush ? " واضغط مسافة للتلوين" : ""}.`}
        onKeyDown={onKeyDown}
        onPointerLeave={() => !painting && onFocusCell(focusCell)}
        className={`relative overflow-hidden rounded-xl bg-ink/10 ${brush ? "cursor-crosshair touch-none" : ""}`}
      >
        <img
          src={map.rectified_url}
          alt={`صورة ${map.wall_name} بعد تعديل المنظور`}
          width={map.rectified_width_px}
          height={map.rectified_height_px}
          draggable={false}
          className="block h-auto w-full select-none"
        />
        <svg viewBox={`0 0 ${map.cols} ${map.rows}`} preserveAspectRatio="none" className="absolute inset-0 h-full w-full">
          {labels.map((label, index) => {
            const row = Math.floor(index / map.cols);
            const col = index % map.cols;
            const cell = byCell.get(label);
            const visible = cell && !layers.hidden.includes(cell.damage_type);
            return (
              <g key={label}>
                <rect
                  x={col}
                  y={row}
                  width={1}
                  height={1}
                  fill={visible ? colorFor(cell.damage_type) : "transparent"}
                  fillOpacity={visible ? severityOpacity[cell.severity] * layers.opacity : 0}
                  stroke={layers.grid ? "var(--color-sand)" : "none"}
                  strokeOpacity={0.45}
                  strokeWidth={0.015}
                  onPointerDown={(event) => {
                    if (!brush) {
                      onFocusCell(label);
                      return;
                    }
                    event.preventDefault();
                    setPainting(true);
                    paint(label);
                    onFocusCell(label);
                  }}
                  onPointerEnter={() => {
                    onFocusCell(label);
                    if (painting) paint(label);
                  }}
                />
                {visible && cell.source === "expert" && (
                  <polygon
                    points={`${col},${row} ${col + 0.26},${row} ${col},${row + 0.26}`}
                    fill="var(--color-sand)"
                    pointerEvents="none"
                  />
                )}
                {changed.has(label) && (
                  <rect
                    x={col + 0.07}
                    y={row + 0.07}
                    width={0.86}
                    height={0.86}
                    fill="none"
                    stroke="var(--color-sand)"
                    strokeWidth={0.07}
                    strokeDasharray="0.14 0.09"
                    pointerEvents="none"
                  />
                )}
              </g>
            );
          })}
          {focusCell && (
            <rect
              x={Number(focusCell.slice(1)) - 1}
              y={focusCell.charCodeAt(0) - 65}
              width={1}
              height={1}
              fill="none"
              stroke="var(--color-ink)"
              strokeWidth={0.08}
              pointerEvents="none"
            />
          )}
        </svg>
      </div>
      <figcaption className="text-xs text-mud">
        الصفوف بالحروف من الأعلى والأعمدة بالأرقام من اليسار. مساحة الخلية{" "}
        <bdi className="tabular-nums">{map.cell_area_m2.toLocaleString("ar-SA")} م²</bdi>. المثلث الفاتح في زاوية الخلية
        يعني أن المختص صححها.
      </figcaption>
    </figure>
  );
}
