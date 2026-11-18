import { damageTypeAr, severityAr } from "@/lib/labels";
import type { TreatmentPlan } from "@/lib/maps";

export function TreatmentPlanView({ plan }: { plan: TreatmentPlan }) {
  return (
    <section className="flex flex-col gap-3">
      <h2 className="text-xl font-bold">خطة المعالجة</h2>
      {plan.review_status === "draft" && (
        <p className="rounded-lg bg-watch/20 p-2 text-sm">
          كتالوج المعالجات (الإصدار {plan.catalog_version}) مسودة لم يعتمدها مختص ترميم بعد. راجع كل خطوة قبل التنفيذ.
        </p>
      )}
      {plan.items.length === 0 && plan.unmatched.length === 0 && <p>لا يوجد تلف يحتاج معالجة في هذا المخطط.</p>}

      {plan.items.map((item) => (
        <article key={`${item.code}-${item.severity}`} className="flex flex-col gap-2 rounded-xl bg-white/70 p-4">
          <header className="flex flex-wrap items-baseline justify-between gap-2">
            <h3 className="font-bold">{item.title_ar}</h3>
            <span className="text-sm">
              {damageTypeAr[item.damage_type] ?? item.damage_type} · {severityAr[item.severity]} ·{" "}
              {item.area_m2.toLocaleString("ar-SA")} م²
            </span>
          </header>
          {item.specialist_required && (
            <p className="text-sm font-bold text-urgent">يتطلب إشراف مختص ترميم.</p>
          )}
          <ol className="list-decimal ps-5 text-sm leading-relaxed">
            {item.steps_ar.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
          {item.materials.length > 0 && (
            <table className="w-full text-sm">
              <caption className="text-start font-bold">المواد (تقديرية)</caption>
              <tbody>
                {item.materials.map((material) => (
                  <tr key={material.name_ar} className="border-t border-clay/30">
                    <td className="py-1">{material.name_ar}</td>
                    <td>
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
          <p className="text-xs">
            المصادر:{" "}
            {item.sources.map((source, index) => (
              <span key={source.url}>
                {index > 0 && "، "}
                <a href={source.url} target="_blank" rel="noreferrer" className="underline">
                  {source.title}
                </a>
              </span>
            ))}
          </p>
        </article>
      ))}

      {plan.unmatched.length > 0 && (
        <p className="rounded-lg bg-urgent/10 p-2 text-sm">
          لا توجد معالجة في الكتالوج لـ:{" "}
          {plan.unmatched.map((u) => `${damageTypeAr[u.damage_type] ?? u.damage_type} (${severityAr[u.severity]})`).join("، ")}.
          يحددها المختص.
        </p>
      )}
      {plan.items.length > 0 && <p className="text-xs leading-relaxed">{plan.quantities_note_ar}</p>}
    </section>
  );
}
