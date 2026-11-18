"use client";

import { useEffect, useId, useRef, useState } from "react";
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
  const cancelRef = useRef<HTMLButtonElement>(null);
  const approveRef = useRef<HTMLButtonElement>(null);
  const returnFocus = useRef(false);
  const approved = map.status === "approved";
  const approveBlocked = busy || !map.field_inspected_at || pendingCount > 0 || unreviewed > 0;
  if (confirming && approveBlocked) setConfirming(false);

  useEffect(() => {
    if (confirming) cancelRef.current?.focus();
    else if (returnFocus.current) approveRef.current?.focus();
    returnFocus.current = false;
  }, [confirming]);

  function cancelApprove() {
    returnFocus.current = true;
    setConfirming(false);
  }

  return (
    <section aria-labelledby="field-title" className="flex flex-col gap-3 rounded-xl bg-white/75 p-3">
      <h2 id="field-title" className="text-lg font-bold">
        الفحص الميداني والاعتماد
      </h2>
      {map.field_inspected_at ? (
        <p>
          فحص المختص الجدار في الموقع يوم{" "}
          <time dateTime={map.field_inspected_at}>{new Date(map.field_inspected_at).toLocaleDateString("ar-SA")}</time>
          {map.field_notes && <>: {map.field_notes}</>}
        </p>
      ) : (
        <p className="text-mud">لا تُعتمد أي معالجة دون فحص ميداني من المختص.</p>
      )}

      {canReview && !approved && !map.field_inspected_at && (
        <div className="flex flex-col gap-2">
          <label htmlFor={notesId} className="text-sm">
            ملاحظات الفحص الميداني
          </label>
          <textarea
            id={notesId}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={2}
            maxLength={2000}
            className="rounded-lg border border-mud bg-white p-2"
          />
          <button
            type="button"
            onClick={() => onInspect(notes)}
            disabled={busy || pendingCount > 0}
            className="min-h-11 w-fit rounded-full border border-ink/30 px-5 text-sm hover:bg-ink hover:text-sand disabled:opacity-50"
          >
            سجّل أني فحصت الجدار ميدانيًا
          </button>
        </div>
      )}

      {canReview && !approved && (
        <div className="flex flex-wrap items-center gap-3">
          {confirming ? (
            <div role="group" aria-label="تأكيد الاعتماد" className="flex flex-wrap items-center gap-2">
              <p className="w-full text-sm font-bold">يُجمَّد المخطط وتُعتمد خطة المعالجة، ولا يمكن التعديل بعدها.</p>
              <button
                type="button"
                onClick={() => {
                  setConfirming(false);
                  onApprove();
                }}
                className="min-h-11 rounded-full bg-sadu px-5 text-sm font-bold text-sand hover:bg-ink"
              >
                اعتمد
              </button>
              <button
                ref={cancelRef}
                type="button"
                onClick={cancelApprove}
                className="min-h-11 rounded-full border border-ink/30 px-5 text-sm hover:bg-ink hover:text-sand"
              >
                إلغاء
              </button>
            </div>
          ) : (
            <button
              ref={approveRef}
              type="button"
              onClick={() => setConfirming(true)}
              disabled={approveBlocked}
              className="min-h-11 rounded-full bg-ink px-5 text-sm font-bold text-sand disabled:opacity-40"
            >
              اعتمد المخطط والمعالجات
            </button>
          )}
          {!map.field_inspected_at && <p className="text-xs text-mud">الاعتماد متاح بعد تسجيل الفحص الميداني.</p>}
          {pendingCount > 0 && <p className="text-xs text-mud">احفظ تعديلاتك أولًا ثم سجّل الفحص أو اعتمد.</p>}
          {unreviewed > 0 && (
            <p className="text-xs text-urgent">
              راجع {countAr(unreviewed, lowConfidenceElements)}: أكّد كلًّا منها أو صحّحه أو احذفه.
            </p>
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
