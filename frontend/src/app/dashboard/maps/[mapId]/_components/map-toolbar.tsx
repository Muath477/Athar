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
                className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm transition-colors ${
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
            className={`rounded-full border border-dashed border-sand/60 px-3 py-1.5 text-sm ${
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
              className={`rounded-full px-3 py-1 text-sm ${
                brush.severity === severity ? "bg-sand font-bold text-ink" : "hover:bg-sand/15"
              }`}
            >
              {severityAr[severity]}
            </button>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button type="button" onClick={onUndo} disabled={!canUndo} className="rounded-full px-3 py-1 text-sm hover:bg-sand/15 disabled:opacity-30" title="Ctrl+Z">
            تراجع
          </button>
          <button type="button" onClick={onRedo} disabled={!canRedo} className="rounded-full px-3 py-1 text-sm hover:bg-sand/15 disabled:opacity-30" title="Ctrl+Shift+Z">
            إعادة
          </button>
          <button
            type="button"
            onClick={onSave}
            disabled={busy || pendingCount === 0}
            className="rounded-full bg-sand px-4 py-1.5 text-sm font-bold text-ink disabled:opacity-30"
          >
            {busy ? "نحفظ…" : pendingCount > 0 ? `احفظ ${countAr(pendingCount, corrections)}` : "احفظ التصحيحات"}
          </button>
          {confirming ? (
            <span className="flex items-center gap-2 rounded-full bg-sadu px-3 py-1 text-sm">
              يُجمَّد المخطط بعد الاعتماد.
              <button type="button" onClick={() => { setConfirming(false); onApprove(); }} className="font-bold underline">
                اعتمد
              </button>
              <button type="button" onClick={() => setConfirming(false)} className="underline">
                إلغاء
              </button>
            </span>
          ) : (
            <button
              type="button"
              onClick={() => setConfirming(true)}
              disabled={busy || pendingCount > 0}
              title={pendingCount > 0 ? "احفظ التصحيحات أولًا" : undefined}
              className="rounded-full bg-sadu px-4 py-1.5 text-sm font-bold text-sand disabled:opacity-30"
            >
              اعتمد المخطط
            </button>
          )}
        </div>
      </div>
      <p className="text-xs text-sand/60">اسحب على الخلايا لتلوينها، أو تنقّل بالأسهم واضغط مسافة. Ctrl+Z للتراجع.</p>
    </section>
  );
}
