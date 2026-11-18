import { cellSourceAr, changeKindAr, confidenceAr, damageTypeAr, severityAr } from "@/lib/labels";
import type { MapCell, MapChange } from "@/lib/maps";

export function CellInspector({
  label,
  cell,
  change,
  editable,
}: {
  label: string | null;
  cell: MapCell | null;
  change: MapChange | null;
  editable: boolean;
}) {
  return (
    <div aria-live="polite" className="no-print flex min-h-11 flex-wrap items-center gap-x-4 gap-y-1 rounded-lg bg-white/60 px-3 py-2 text-sm">
      {!label ? (
        <span className="text-mud">
          {editable ? "مرّر على الخلايا لترى تفاصيلها، واسحب لتلوينها بالفرشاة." : "مرّر على أي خلية لترى تفاصيلها."}
        </span>
      ) : (
        <>
          <strong className="font-bold tabular-nums">
            <bdi>{label}</bdi>
          </strong>
          {cell ? (
            <>
              <span>{damageTypeAr[cell.damage_type] ?? cell.damage_type}</span>
              <span>الخطورة: {severityAr[cell.severity]}</span>
              <span className="text-mud">
                المصدر: {cellSourceAr[cell.source]}
                {cell.source === "model" && ` · ثقة ${confidenceAr[cell.confidence]}`}
              </span>
            </>
          ) : (
            <span className="text-mud">سليمة</span>
          )}
          {change && <span className="font-bold text-sadu">{changeKindAr[change.kind]}</span>}
        </>
      )}
    </div>
  );
}
