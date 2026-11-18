"use client";

import { useId, useState } from "react";
import { MarginNote } from "@/components/brand/margin-note";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import type { DamageMap } from "@/lib/maps";
import { countAr, lowConfidenceElements } from "@/lib/plural";

const ACTION_AR = { add: "أضاف", update: "عدّل", delete: "حذف" } as const;

type Props = {
  map: DamageMap;
  canReview: boolean;
  busy: boolean;
  pendingCount: number;
  unreviewed: number;
  onInspect: (notes: string) => void;
  onApprove: () => void;
};

export function FieldReview({ map, canReview, busy, pendingCount, unreviewed, onInspect, onApprove }: Props) {
  const [notes, setNotes] = useState("");
  const [confirming, setConfirming] = useState(false);
  const notesId = useId();
  const approved = map.status === "approved";
  const approveBlocked = busy || !map.field_inspected_at || pendingCount > 0 || unreviewed > 0;
  if (confirming && approveBlocked) setConfirming(false);

  return (
    <section aria-labelledby="field-title" className="flex flex-col gap-3 border-t border-line pt-3">
      <h2 id="field-title" className="text-lg font-bold">
        الفحص الميداني والاعتماد
      </h2>
      {map.field_inspected_at ? (
        <MarginNote label="حاشية المختص">
          فحص الجدار في الموقع يوم{" "}
          <time dateTime={map.field_inspected_at}>{new Date(map.field_inspected_at).toLocaleDateString("ar-SA")}</time>
          {map.field_notes && <>: {map.field_notes}</>}
        </MarginNote>
      ) : (
        <p className="text-mud">لا تُعتمد أي معالجة دون فحص ميداني من المختص.</p>
      )}

      {canReview && !approved && !map.field_inspected_at && (
        <div className="flex flex-col gap-2">
          <Label htmlFor={notesId}>ملاحظات الفحص الميداني</Label>
          <Textarea
            id={notesId}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={2}
            maxLength={2000}
          />
          <Button
            type="button"
            variant="outline"
            onClick={() => onInspect(notes)}
            disabled={busy || pendingCount > 0}
            className="w-fit"
          >
            سجّل أني فحصت الجدار ميدانيًا
          </Button>
        </div>
      )}

      {canReview && !approved && (
        <div className="flex flex-wrap items-center gap-3">
          <AlertDialog open={confirming} onOpenChange={setConfirming}>
            <AlertDialogTrigger asChild>
              <Button type="button" disabled={approveBlocked}>
                اعتمد المخطط والمعالجات
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>اعتماد المخطط</AlertDialogTitle>
                <AlertDialogDescription>
                  يُجمَّد المخطط وتُعتمد خطة المعالجة، ولا يمكن التعديل بعدها.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogAction onClick={onApprove}>اعتمد</AlertDialogAction>
                <AlertDialogCancel>إلغاء</AlertDialogCancel>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
          {!map.field_inspected_at && <p className="text-xs text-mud">الاعتماد متاح بعد تسجيل الفحص الميداني.</p>}
          {pendingCount > 0 && <p className="text-xs text-mud">احفظ تعديلاتك أولًا ثم سجّل الفحص أو اعتمد.</p>}
          {unreviewed > 0 && (
            <MarginNote label="حاشية: ثقة منخفضة" className="basis-full">
              راجع {countAr(unreviewed, lowConfidenceElements)}: أكّد كلًّا منها أو صحّحه أو احذفه.
            </MarginNote>
          )}
        </div>
      )}

      {map.correction_log.length > 0 && (
        <details className="text-sm">
          <summary className="cursor-pointer">
            سجل التصحيحات ({map.correction_log.length.toLocaleString("ar-SA")})
          </summary>
          <ol className="mt-2 flex flex-col gap-1">
            {[...map.correction_log].reverse().map((entry, i) => (
              <li key={`${entry.at}-${i}`} className="text-mud">
                <time dateTime={entry.at}>{new Date(entry.at).toLocaleString("ar-SA")}</time> ·{" "}
                {ACTION_AR[entry.action]} <bdi>{entry.element_id}</bdi>
              </li>
            ))}
          </ol>
        </details>
      )}
    </section>
  );
}
