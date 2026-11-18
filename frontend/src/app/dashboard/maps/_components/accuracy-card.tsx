"use client";

import { useEffect, useState } from "react";
import { colorFor } from "@/lib/damage-palette";
import { damageTypeAr } from "@/lib/labels";
import { type MapAccuracy, getAccuracy } from "@/lib/maps";
import { approvedMaps, countAr } from "@/lib/plural";

export function AccuracyCard() {
  const [accuracy, setAccuracy] = useState<MapAccuracy | null>(null);

  useEffect(() => {
    getAccuracy().then(setAccuracy, () => setAccuracy(null));
  }, []);

  if (!accuracy) return null;

  const scored = accuracy.by_type.filter((t) => t.true_positives + t.false_positives + t.false_negatives > 0);

  return (
    <section className="flex flex-col gap-3 border-t border-line pt-5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-xl font-bold">هل يوافق النموذج المختص؟</h2>
        {accuracy.maps > 0 && (
          <p className="text-sm text-mud">
            من {countAr(accuracy.maps, approvedMaps)} · اتفاق على وجود التلف{" "}
            <strong className="tabular-nums text-ink">{percent(accuracy.damaged_vs_sound_accuracy)}</strong>
          </p>
        )}
      </div>
      {accuracy.maps === 0 ? (
        <p className="max-w-prose text-sm leading-relaxed text-mud">
          تظهر الدقة هنا بعد اعتماد أول مخطط حلّله النموذج: نقارن ما قاله النموذج بما اعتمده المختص خلية خلية.
        </p>
      ) : (
        <table className="w-full max-w-2xl text-sm">
          <thead className="text-mud">
            <tr>
              <th className="py-1 text-start font-normal">نوع التلف</th>
              <th className="py-1 text-start font-normal">الدقة (ما قاله النموذج وصح)</th>
              <th className="py-1 text-start font-normal">الاستدعاء (ما اكتشفه من الموجود)</th>
            </tr>
          </thead>
          <tbody>
            {scored.map((t) => (
              <tr key={t.damage_type} className="border-t border-line">
                <td className="py-2">
                  <span className="flex items-center gap-2">
                    <span aria-hidden className="h-3 w-3 rounded-sm" style={{ background: colorFor(t.damage_type) }} />
                    {damageTypeAr[t.damage_type] ?? t.damage_type}
                  </span>
                </td>
                <td className="py-2">
                  <Meter value={t.precision} />
                </td>
                <td className="py-2">
                  <Meter value={t.recall} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

function Meter({ value }: { value: number | null }) {
  if (value === null) return <span className="text-mud">لا بيانات</span>;
  return (
    <span className="flex items-center gap-2">
      <span className="h-1.5 w-24 overflow-hidden rounded-xs bg-clay">
        <span className="block h-full bg-ink" style={{ inlineSize: `${value * 100}%` }} />
      </span>
      <span className="tabular-nums">{percent(value)}</span>
    </span>
  );
}

function percent(value: number | null): string {
  return value === null ? "—" : `${Math.round(value * 100).toLocaleString("ar-SA")}٪`;
}
