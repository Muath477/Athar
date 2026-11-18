"use client";

import { useEffect, useState } from "react";
import { damageTypeAr } from "@/lib/labels";
import { type MapAccuracy, getAccuracy } from "@/lib/maps";

export function AccuracyCard() {
  const [accuracy, setAccuracy] = useState<MapAccuracy | null>(null);

  useEffect(() => {
    getAccuracy().then(setAccuracy, () => setAccuracy(null));
  }, []);

  if (!accuracy) return null;

  return (
    <section className="flex flex-col gap-2 rounded-xl bg-white/60 p-4">
      <h2 className="font-bold">دقة النموذج مقارنةً بقرار المختص</h2>
      {accuracy.maps === 0 ? (
        <p className="text-sm">تظهر الدقة بعد اعتماد أول مخطط حلّله النموذج.</p>
      ) : (
        <>
          <p className="text-sm">
            {accuracy.maps.toLocaleString("ar-SA")} مخطط معتمد. اتفاق النموذج والمختص على وجود التلف من عدمه:{" "}
            <strong>{percent(accuracy.damaged_vs_sound_accuracy)}</strong>
          </p>
          <table className="w-full text-sm">
            <thead>
              <tr>
                <th className="text-start">نوع التلف</th>
                <th className="text-start">الدقة</th>
                <th className="text-start">الاستدعاء</th>
              </tr>
            </thead>
            <tbody>
              {accuracy.by_type
                .filter((t) => t.true_positives + t.false_positives + t.false_negatives > 0)
                .map((t) => (
                  <tr key={t.damage_type} className="border-t border-clay/30">
                    <td className="py-1">{damageTypeAr[t.damage_type] ?? t.damage_type}</td>
                    <td>{percent(t.precision)}</td>
                    <td>{percent(t.recall)}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </>
      )}
    </section>
  );
}

function percent(value: number | null): string {
  return value === null ? "—" : `${Math.round(value * 100).toLocaleString("ar-SA")}٪`;
}
