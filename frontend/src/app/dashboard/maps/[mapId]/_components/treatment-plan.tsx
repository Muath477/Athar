"use client";

import { useState } from "react";
import { colorFor } from "@/lib/damage-palette";
import { damageTypeAr, severityAr } from "@/lib/labels";
import type { TreatmentPlan } from "@/lib/maps";

export function TreatmentPlanView({ plan, pendingCount }: { plan: TreatmentPlan; pendingCount: number }) {
  const [copied, setCopied] = useState(false);
  const totals = materialTotals(plan);

  async function copyList() {
    const text = totals.map((m) => `${m.name_ar}: ${m.quantity.toLocaleString("ar-SA")} ${m.unit_ar}`).join("\n");
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  }

  return (
    <section className="flex flex-col gap-4 border-t border-clay/40 pt-5">
      <header className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-2xl font-bold">خطة المعالجة</h2>
        {pendingCount > 0 && <p className="text-sm text-mud">تتحدث الخطة بعد حفظ التصحيحات.</p>}
      </header>

      {plan.review_status === "draft" && (
        <p className="max-w-prose border-s-4 border-watch bg-watch/15 p-3 text-sm leading-relaxed">
          كتالوج المعالجات (الإصدار <bdi>{plan.catalog_version}</bdi>) مسودة لم يعتمدها مختص ترميم بعد. راجع كل خطوة قبل
          التنفيذ.
        </p>
      )}

      {plan.items.length === 0 && plan.unmatched.length === 0 ? (
        <p>لا يوجد تلف يحتاج معالجة في هذا المخطط.</p>
      ) : (
        <div className="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(16rem,1fr)]">
          <ol className="flex flex-col gap-3">
            {plan.items.map((item, index) => (
              <li key={`${item.code}-${item.severity}`}>
                <details open={index === 0} className="group rounded-xl bg-white/70">
                  <summary className="flex cursor-pointer list-none flex-wrap items-center justify-between gap-2 p-4">
                    <span className="flex items-center gap-3">
                      <span aria-hidden className="h-8 w-1.5 rounded-full" style={{ background: colorFor(item.damage_type) }} />
                      <span className="flex flex-col">
                        <span className="font-bold">{item.title_ar}</span>
                        <span className="text-sm text-mud">
                          {damageTypeAr[item.damage_type] ?? item.damage_type} · {severityAr[item.severity]} ·{" "}
                          <bdi className="tabular-nums">{item.area_m2.toLocaleString("ar-SA")} م²</bdi>
                        </span>
                      </span>
                    </span>
                    <span className="flex items-center gap-2 text-sm">
                      {item.specialist_required && <span className="rounded-full bg-urgent/10 px-2.5 py-0.5 font-bold text-urgent">بإشراف مختص</span>}
                      <span aria-hidden className="transition-transform group-open:rotate-180">▾</span>
                    </span>
                  </summary>
                  <div className="flex flex-col gap-3 px-4 pb-4">
                    {item.locations.length > 0 && (
                      <p className="text-sm">
                        <span className="text-mud">مواقع الاستخدام على الواجهة: </span>
                        {item.locations.map((location, i) => (
                          <span key={location}>
                            <bdi>{location}</bdi>
                            {i < item.locations.length - 1 && "، "}
                          </span>
                        ))}
                      </p>
                    )}
                    <ol className="list-[arabic-indic] ps-6 leading-relaxed">
                      {item.steps_ar.map((step) => (
                        <li key={step}>{step}</li>
                      ))}
                    </ol>
                    {item.materials.length > 0 && (
                      <table className="w-full text-sm">
                        <caption className="pb-1 text-start font-bold">المواد لهذه المساحة (تقديرية)</caption>
                        <tbody>
                          {item.materials.map((material) => (
                            <tr key={material.name_ar} className="border-t border-clay/30">
                              <td className="py-1.5">{material.name_ar}</td>
                              <td className="tabular-nums">
                                {material.quantity.toLocaleString("ar-SA")} {material.unit_ar}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                    {item.tools_ar.length > 0 && (
                      <p className="text-sm">
                        <span className="font-bold">الأدوات: </span>
                        {item.tools_ar.join("، ")}
                      </p>
                    )}
                    <p className="text-xs text-mud">
                      المصادر:{" "}
                      {item.sources.map((source, i) => (
                        <span key={source.url}>
                          {i > 0 && "، "}
                          <a href={source.url} target="_blank" rel="noreferrer" className="underline">
                            {source.title}
                          </a>
                        </span>
                      ))}
                    </p>
                  </div>
                </details>
              </li>
            ))}
          </ol>

          {totals.length > 0 && (
            <aside className="flex h-fit flex-col gap-2 rounded-xl bg-ink p-4 text-sand">
              <h3 className="font-bold">قائمة المواد للجدار كله</h3>
              <ul className="flex flex-col text-sm">
                {totals.map((m) => (
                  <li key={m.name_ar + m.unit_ar} className="flex justify-between gap-3 border-b border-sand/15 py-1.5">
                    <span>{m.name_ar}</span>
                    <span className="tabular-nums">
                      {m.quantity.toLocaleString("ar-SA")} {m.unit_ar}
                    </span>
                  </li>
                ))}
              </ul>
              <button type="button" onClick={copyList} className="no-print self-start rounded-full bg-sand px-3 py-1 text-sm font-bold text-ink">
                {copied ? "نُسخت القائمة" : "انسخ القائمة"}
              </button>
              <p className="text-xs leading-relaxed text-sand/70">{plan.quantities_note_ar}</p>
            </aside>
          )}
        </div>
      )}

      {plan.unmatched.length > 0 && (
        <p className="border-s-4 border-urgent bg-urgent/10 p-3 text-sm">
          لا توجد معالجة في الكتالوج لـ:{" "}
          {plan.unmatched.map((u) => `${damageTypeAr[u.damage_type] ?? u.damage_type} (${severityAr[u.severity]})`).join("، ")}.
          يحددها المختص.
        </p>
      )}
    </section>
  );
}

function materialTotals(plan: TreatmentPlan) {
  const totals = new Map<string, { name_ar: string; unit_ar: string; quantity: number }>();
  for (const item of plan.items) {
    for (const material of item.materials) {
      const key = material.name_ar + "|" + material.unit_ar;
      const current = totals.get(key) ?? { name_ar: material.name_ar, unit_ar: material.unit_ar, quantity: 0 };
      current.quantity = Math.round((current.quantity + material.quantity) * 10) / 10;
      totals.set(key, current);
    }
  }
  return [...totals.values()];
}
