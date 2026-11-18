"use client";

import { colorFor, severityOpacity } from "@/lib/damage-palette";
import { changeKindAr, damageTypeAr, severityAr } from "@/lib/labels";
import { type DamageMap, type MapCell, type MapChanges, cellLabel } from "@/lib/maps";

export function DamageGrid({
  map,
  cells,
  selected,
  changes,
  onSelect,
}: {
  map: DamageMap;
  cells: MapCell[];
  selected: string | null;
  changes: MapChanges | null;
  onSelect?: (cell: string) => void;
}) {
  const byCell = new Map(cells.map((c) => [c.cell, c]));
  const changed = new Map((changes?.items ?? []).map((c) => [c.cell, c]));
  const allCells = Array.from({ length: map.rows * map.cols }, (_, i) => cellLabel(Math.floor(i / map.cols), i % map.cols));

  return (
    <figure className="flex flex-col gap-2">
      <div dir="ltr" className="relative overflow-hidden rounded-xl bg-ink/10">
        <img
          src={map.rectified_url}
          alt={`صورة ${map.wall_name} بعد تعديل المنظور`}
          width={map.rectified_width_px}
          height={map.rectified_height_px}
          className="block h-auto w-full"
        />
        <svg
          viewBox={`0 0 ${map.cols} ${map.rows}`}
          preserveAspectRatio="none"
          className="absolute inset-0 h-full w-full"
          role="group"
          aria-label="شبكة التلف"
        >
          {allCells.map((label, index) => {
            const row = Math.floor(index / map.cols);
            const col = index % map.cols;
            const cell = byCell.get(label);
            const change = changed.get(label);
            const description = [
              label,
              cell ? `${damageTypeAr[cell.damage_type] ?? cell.damage_type} · ${severityAr[cell.severity]}` : "سليم",
              change ? changeKindAr[change.kind] : null,
            ]
              .filter(Boolean)
              .join(" · ");
            return (
              <g key={label}>
                <rect
                  x={col}
                  y={row}
                  width={1}
                  height={1}
                  fill={cell ? colorFor(cell.damage_type) : "transparent"}
                  fillOpacity={cell ? severityOpacity[cell.severity] : 0}
                  stroke="rgba(255,255,255,0.35)"
                  strokeWidth={0.02}
                  className={onSelect ? "cursor-pointer" : undefined}
                  onClick={onSelect ? () => onSelect(label) : undefined}
                >
                  <title>{description}</title>
                </rect>
                {change && (
                  <rect
                    x={col + 0.06}
                    y={row + 0.06}
                    width={0.88}
                    height={0.88}
                    fill="none"
                    stroke="#ffffff"
                    strokeWidth={0.08}
                    strokeDasharray="0.15 0.1"
                    pointerEvents="none"
                  />
                )}
                {selected === label && (
                  <rect x={col} y={row} width={1} height={1} fill="none" stroke="#1f1a16" strokeWidth={0.1} pointerEvents="none" />
                )}
              </g>
            );
          })}
        </svg>
      </div>
      <figcaption className="text-xs">
        الشبكة {map.rows.toLocaleString("ar-SA")} صفوف × {map.cols.toLocaleString("ar-SA")} أعمدة، مساحة الخلية{" "}
        {map.cell_area_m2.toLocaleString("ar-SA")} م². الصفوف بالحروف من الأعلى والأعمدة بالأرقام من اليسار.
      </figcaption>
    </figure>
  );
}
