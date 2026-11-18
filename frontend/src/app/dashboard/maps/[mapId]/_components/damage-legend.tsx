import { colorFor, severityOpacity } from "@/lib/damage-palette";
import { damageTypeAr, severityAr } from "@/lib/labels";
import type { DamageMap, MapCell } from "@/lib/maps";

export function DamageLegend({ map, cells }: { map: DamageMap; cells: MapCell[] }) {
  const counts = new Map<string, number>();
  for (const cell of cells) counts.set(cell.damage_type, (counts.get(cell.damage_type) ?? 0) + 1);

  return (
    <section className="flex flex-col gap-3 rounded-xl bg-white/60 p-3 text-sm" aria-label="مفتاح الألوان">
      <h2 className="font-bold">مفتاح الألوان</h2>
      <ul className="flex flex-col gap-1.5">
        {map.damage_types.map((type) => (
          <li key={type} className="flex items-center justify-between gap-2">
            <span className="flex items-center gap-2">
              <span aria-hidden className="inline-block h-4 w-4 rounded" style={{ background: colorFor(type) }} />
              {damageTypeAr[type] ?? type}
            </span>
            <span>{area(counts.get(type) ?? 0, map.cell_area_m2)}</span>
          </li>
        ))}
      </ul>
      <div className="flex flex-col gap-1">
        <span>قوة اللون تعني الخطورة:</span>
        <div className="flex gap-3">
          {Object.entries(severityOpacity).map(([severity, opacity]) => (
            <span key={severity} className="flex items-center gap-1">
              <span aria-hidden className="inline-block h-4 w-4 rounded bg-ink" style={{ opacity }} />
              {severityAr[severity]}
            </span>
          ))}
        </div>
      </div>
      <p>
        المساحة المتضررة: <strong>{area(cells.length, map.cell_area_m2)}</strong>
      </p>
    </section>
  );
}

function area(cells: number, cellArea: number): string {
  if (cells === 0) return "—";
  return `${(cells * cellArea).toLocaleString("ar-SA", { maximumFractionDigits: 1 })} م²`;
}
