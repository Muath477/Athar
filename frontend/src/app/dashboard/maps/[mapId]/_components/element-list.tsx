import { classAr, measureAr } from "@/lib/elements";
import { severityAr } from "@/lib/labels";
import type { GlossaryEntry, MapElement } from "@/lib/maps";

type Props = {
  elements: MapElement[];
  glossary: Record<string, GlossaryEntry>;
  selectedId: string | null;
  onSelect: (id: string) => void;
};

export function ElementList({ elements, glossary, selectedId, onSelect }: Props) {
  const review = elements.filter((e) => e.needs_review).length;
  return (
    <section aria-labelledby="elements-title" className="flex flex-col gap-2">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 id="elements-title" className="text-lg font-bold">
          عناصر التلف
        </h2>
        {review > 0 && (
          <p className="text-sm font-bold text-urgent">
            {review.toLocaleString("ar-SA")} بثقة منخفضة، لا تُعتمد قبل أن يراجعها المختص
          </p>
        )}
      </div>
      {elements.length === 0 ? (
        <p className="text-mud">لا عناصر بعد. ارسم التلف على الصورة.</p>
      ) : (
        <div className="overflow-x-auto rounded-xl bg-white/75">
          <table className="w-full text-sm">
            <thead className="text-start text-mud">
              <tr className="border-b border-clay/30">
                <th className="p-2 text-start font-normal">العنصر</th>
                <th className="p-2 text-start font-normal">النوع</th>
                <th className="p-2 text-start font-normal">الموقع</th>
                <th className="p-2 text-start font-normal">القياس</th>
                <th className="p-2 text-start font-normal">الفئة</th>
                <th className="p-2 text-start font-normal">الشدة</th>
                <th className="p-2 text-start font-normal">المعد</th>
              </tr>
            </thead>
            <tbody>
              {elements.map((e) => (
                <tr
                  key={e.id}
                  className={`border-b border-clay/20 last:border-0 ${e.id === selectedId ? "bg-sand" : ""}`}
                >
                  <td className="p-2">
                    <button
                      type="button"
                      onClick={() => onSelect(e.id)}
                      aria-pressed={e.id === selectedId}
                      className="font-bold underline-offset-2 hover:underline"
                    >
                      <bdi>{e.id}</bdi>
                    </button>
                    {e.needs_review && <span className="ms-2 text-xs font-bold text-urgent">ثقة منخفضة</span>}
                  </td>
                  <td className="p-2">
                    <span
                      className="me-1.5 inline-block size-3 rounded-sm border border-ink/20 align-middle"
                      style={{ background: glossary[e.damage_type]?.color }}
                    />
                    {glossary[e.damage_type]?.name_ar ?? e.damage_type}
                  </td>
                  <td className="p-2 tabular-nums">
                    <bdi>{e.location}</bdi>
                  </td>
                  <td className="p-2 tabular-nums">{measureAr(e)}</td>
                  <td className="p-2">{e.damage_class ? (classAr[e.damage_class] ?? e.damage_class) : "—"}</td>
                  <td className={`p-2 ${e.severity === "urgent" ? "font-bold text-urgent" : ""}`}>{severityAr[e.severity]}</td>
                  <td className="p-2">{e.source === "expert" ? "المختص" : "النموذج"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
