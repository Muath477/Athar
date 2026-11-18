"use client";

import { useState } from "react";
import { colorFor } from "@/lib/damage-palette";
import { damageTypeAr, severityAr } from "@/lib/labels";
import { corrections, countAr } from "@/lib/plural";

export type Brush = { damage_type: string; severity: string };

const SEVERITIES = ["watch", "moderate", "urgent"];

export function MapToolbar({
  damageTypes,
  brush,
  onBrush,
  pendingCount,
  unsaved,
  fieldInspected,
  unreviewed,
  canUndo,
  canRedo,
  busy,
  onUndo,
  onRedo,
  onSave,
  onApprove,
}: {
  damageTypes: string[];
  brush: Brush;
  onBrush: (brush: Brush) => void;
  pendingCount: number;
  unsaved: number;
  fieldInspected: boolean;
  unreviewed: number;
  canUndo: boolean;
  canRedo: boolean;
  busy: boolean;
  onUndo: () => void;
  onRedo: () => void;
  onSave: () => void;
  onApprove: () => void;
}) {
  const [confirming, setConfirming] = useState(false);
  const erasing = brush.damage_type === "none";
  const approveBlocked = busy || !fieldInspected || unsaved > 0 || unreviewed > 0;
  const focusRing = "focus-visible:outline-sand";
  if (confirming && approveBlocked) setConfirming(false);

  return (
    <section aria-label="أدوات التصحيح" className="no-print flex flex-col gap-3 rounded-xl bg-ink p-3 text-sand">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <span className="text-sm text-sand/70">الفرشاة</span>
        <div role="radiogroup" aria-label="نوع التلف" className="flex flex-wrap gap-1.5">
          {damageTypes.map((type) => {
            const selected = brush.damage_type === type;
            return (
              <button
                key={type}
                type="button"
                role="radio"
                aria-checked={selected}
                onClick={() => onBrush({ ...brush, damage_type: type })}
                className={`flex min-h-11 items-center gap-1.5 rounded-full px-3 text-sm transition-colors ${focusRing} ${
                  selected ? "bg-sand text-ink" : "hover:bg-sand/15"
                }`}
              >
                <span aria-hidden className="h-3 w-3 rounded-sm" style={{ background: colorFor(type) }} />
                {damageTypeAr[type] ?? type}
              </button>
            );
          })}
          <button
            type="button"
            role="radio"
            aria-checked={erasing}
            onClick={() => onBrush({ ...brush, damage_type: "none" })}
            className={`min-h-11 rounded-full border border-dashed border-sand/60 px-3 text-sm ${focusRing} ${
              erasing ? "bg-sand text-ink" : "hover:bg-sand/15"
            }`}
          >
            ممحاة: سليمة
          </button>
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div role="radiogroup" aria-label="الخطورة" className={`flex items-center gap-1 ${erasing ? "opacity-40" : ""}`}>
          <span className="me-2 text-sm text-sand/70">الخطورة</span>
          {SEVERITIES.map((severity) => (
            <button
              key={severity}
              type="button"
              role="radio"
              aria-checked={brush.severity === severity}
              disabled={erasing}
              onClick={() => onBrush({ ...brush, severity })}
              className={`min-h-11 rounded-full px-3 text-sm ${focusRing} ${
                brush.severity === severity ? "bg-sand font-bold text-ink" : "hover:bg-sand/15"
              }`}
            >
              {severityAr[severity]}
            </button>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={onUndo}
            disabled={!canUndo}
            aria-keyshortcuts="Control+Z"
            className={`min-h-11 rounded-full px-3 text-sm hover:bg-sand/15 disabled:opacity-30 ${focusRing}`}
          >
            تراجع
          </button>
          <button
            type="button"
            onClick={onRedo}
            disabled={!canRedo}
            aria-keyshortcuts="Control+Shift+Z"
            className={`min-h-11 rounded-full px-3 text-sm hover:bg-sand/15 disabled:opacity-30 ${focusRing}`}
          >
            إعادة
          </button>
          <button
            type="button"
            onClick={onSave}
            disabled={busy || pendingCount === 0}
            className={`min-h-11 rounded-full bg-sand px-4 text-sm font-bold text-ink disabled:opacity-30 ${focusRing}`}
          >
            {busy ? "نحفظ…" : pendingCount > 0 ? `احفظ ${countAr(pendingCount, corrections)}` : "احفظ التصحيحات"}
          </button>
          {confirming ? (
            <span role="group" aria-label="تأكيد الاعتماد" className="flex items-center gap-2 rounded-full bg-mud ps-3 text-sm text-sand">
              يُجمَّد المخطط بعد الاعتماد.
              <button
                type="button"
                onClick={() => {
                  setConfirming(false);
                  onApprove();
                }}
                className={`min-h-11 px-2 font-bold underline ${focusRing}`}
              >
                اعتمد
              </button>
              <button type="button" onClick={() => setConfirming(false)} className={`min-h-11 pe-3 ps-2 underline ${focusRing}`}>
                إلغاء
              </button>
            </span>
          ) : (
            <button
              type="button"
              onClick={() => setConfirming(true)}
              disabled={approveBlocked}
              aria-describedby={approveBlocked && !busy ? "grid-approve-reason" : undefined}
              className={`min-h-11 rounded-full bg-sadu px-4 text-sm font-bold text-sand disabled:opacity-30 ${focusRing}`}
            >
              اعتمد المخطط
            </button>
          )}
        </div>
      </div>
      {!busy && approveBlocked && (
        <p id="grid-approve-reason" className="text-xs text-sand/70">
          {!fieldInspected
            ? "الاعتماد متاح بعد تسجيل الفحص الميداني."
            : unsaved > 0
              ? "احفظ التعديلات أولًا ثم اعتمد."
              : "راجع العناصر منخفضة الثقة في وضع «عناصر التلف بالمسرد» قبل الاعتماد."}
        </p>
      )}
      <p className="text-xs text-sand/60">
        اسحب على الخلايا لتلوينها، أو تنقّل بالأسهم واضغط زر المسافة.{" "}
        <kbd dir="ltr" className="rounded bg-clay/20 px-1">
          Ctrl+Z
        </kbd>{" "}
        للتراجع.
      </p>
    </section>
  );
}
