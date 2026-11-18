import { colorFor, severityOpacity } from "@/lib/damage-palette";
import { damageTypeAr, severityAr } from "@/lib/labels";
import type { DamageMap, MapCell } from "@/lib/maps";

export function DamageLegend({
  map,
  cells,
  hidden,
  onToggle,
}: {
  map: DamageMap;
  cells: MapCell[];
  hidden: string[];
  onToggle: (type: string) => void;
}) {
  const counts = new Map<string, number>();
  for (const cell of cells) counts.set(cell.damage_type, (counts.get(cell.damage_type) ?? 0) + 1);
  const total = map.rows * map.cols;
  const damaged = cells.length;

  return (
    <aside aria-label="مفتاح الألوان" className="flex flex-col gap-4 text-sm">
      <section className="flex flex-col gap-2">
        <h2 className="font-bold">مفتاح الألوان</h2>
        <p className="no-print text-xs text-mud">اضغط على نوع لإخفائه من الطبقة.</p>
        <div className="flex h-3 overflow-hidden rounded-full bg-clay/25" role="img" aria-label="توزيع المساحة المتضررة حسب النوع">
          {map.damage_types.map((type) =>
            counts.get(type) ? (
              <span key={type} style={{ inlineSize: `${((counts.get(type) ?? 0) / total) * 100}%`, background: colorFor(type) }} />
            ) : null,
          )}
        </div>
        <ul className="flex flex-col">
          {map.damage_types.map((type) => {
            const count = counts.get(type) ?? 0;
            const off = hidden.includes(type);
            return (
              <li key={type} className="flex items-center justify-between gap-2 border-b border-clay/25 py-1.5">
                <button
                  type="button"
                  onClick={() => onToggle(type)}
                  aria-pressed={!off}
                  title={off ? "أظهر هذا النوع" : "أخفِ هذا النوع"}
                  className={`flex items-center gap-2 text-start ${off ? "text-mud line-through" : ""}`}
                >
                  <span
                    aria-hidden
                    className="h-4 w-4 shrink-0 rounded"
                    style={{ background: colorFor(type), opacity: off ? 0.3 : 1 }}
                  />
                  {damageTypeAr[type] ?? type}
                </button>
                <bdi className="tabular-nums text-mud">
                  {count ? `${(count * map.cell_area_m2).toLocaleString("ar-SA", { maximumFractionDigits: 1 })} م²` : "—"}
                </bdi>
              </li>
            );
          })}
        </ul>
      </section>

      <section className="flex flex-col gap-1.5">
        <h3 className="font-bold">قوة اللون = الخطورة</h3>
        <div className="flex gap-3">
          {Object.entries(severityOpacity).map(([severity, opacity]) => (
            <span key={severity} className="flex items-center gap-1.5">
              <span aria-hidden className="h-4 w-4 rounded bg-ink" style={{ opacity }} />
              {severityAr[severity]}
            </span>
          ))}
        </div>
      </section>

      <p className="border-t border-clay/40 pt-3 text-base">
        <strong className="tabular-nums">{Math.round((damaged / total) * 100).toLocaleString("ar-SA")}٪</strong> من
        الجدار متضرر ({damaged.toLocaleString("ar-SA")} من {total.toLocaleString("ar-SA")} خلية)
      </p>
    </aside>
  );
}
