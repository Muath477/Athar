import { changeKindAr, damageTypeAr } from "@/lib/labels";
import type { MapChanges } from "@/lib/maps";

export function MapChangesList({ changes }: { changes: MapChanges }) {
  const since = new Date(changes.previous_created_at).toLocaleDateString("ar-SA");
  return (
    <section className="flex flex-col gap-2">
      <h2 className="font-bold">التغييرات منذ آخر مخطط معتمد ({since})</h2>
      {!changes.comparable ? (
        <p className="text-sm">تختلف شبكة هذا المخطط عن السابق، لذا لا يمكن مقارنة الخلايا.</p>
      ) : changes.items.length === 0 ? (
        <p className="text-sm">لا تغيير في حالة الجدار.</p>
      ) : (
        <ul className="grid gap-1 text-sm sm:grid-cols-2">
          {changes.items.map((change) => (
            <li key={change.cell} className="rounded-lg bg-white/60 p-2">
              <strong>{change.cell}</strong> · {changeKindAr[change.kind]}
              {change.after_type && ` · ${damageTypeAr[change.after_type] ?? change.after_type}`}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
