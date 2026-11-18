import { MarginNote } from "@/components/brand/margin-note";
import { SeverityLabel } from "@/components/brand/severity-label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { classAr, measureAr } from "@/lib/elements";
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
      <h2 id="elements-title" tabIndex={-1} className="text-lg font-bold">
        عناصر التلف
      </h2>
      {review > 0 && (
        <MarginNote label="حاشية: ثقة منخفضة">
          عناصر بثقة منخفضة: {review.toLocaleString("ar-SA")}. لا تُعتمد قبل أن يراجعها المختص
        </MarginNote>
      )}
      {elements.length === 0 ? (
        <p className="text-mud">لا عناصر بعد. ارسم التلف على الصورة.</p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>العنصر</TableHead>
              <TableHead>النوع</TableHead>
              <TableHead>الموقع</TableHead>
              <TableHead>القياس</TableHead>
              <TableHead className="hidden sm:table-cell">الفئة</TableHead>
              <TableHead>الشدة</TableHead>
              <TableHead className="hidden sm:table-cell">المصدر</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {elements.map((e) => (
              <TableRow key={e.id} data-state={e.id === selectedId ? "selected" : undefined}>
                <TableCell>
                  <button
                    type="button"
                    onClick={() => onSelect(e.id)}
                    aria-pressed={e.id === selectedId}
                    className="min-h-6 cursor-pointer font-bold underline-offset-4 hover:text-sadu hover:underline"
                  >
                    <bdi>{e.id}</bdi>
                  </button>
                  {e.needs_review && <span className="ms-2 text-xs font-bold text-sadu">ثقة منخفضة</span>}
                </TableCell>
                <TableCell>
                  <span
                    className="me-1.5 inline-block size-3 rounded-xs border border-ink/20 align-middle"
                    style={{ background: glossary[e.damage_type]?.color }}
                  />
                  {glossary[e.damage_type]?.name_ar ?? e.damage_type}
                </TableCell>
                <TableCell>
                  <bdi>{e.location}</bdi>
                </TableCell>
                <TableCell>{measureAr(e)}</TableCell>
                <TableCell className="hidden sm:table-cell">
                  {e.damage_class ? (classAr[e.damage_class] ?? e.damage_class) : "—"}
                </TableCell>
                <TableCell>
                  <SeverityLabel severity={e.severity} />
                </TableCell>
                <TableCell className="hidden sm:table-cell">{e.source === "expert" ? "المختص" : "النموذج"}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </section>
  );
}
