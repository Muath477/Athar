"use client";

import { useState } from "react";
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
  if (confirming && approveBlocked) setConfirming(false);

  return (
    <section aria-label="أدوات التصحيح" className="no-print flex flex-col gap-3 rounded-sm border border-line bg-white p-3">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <span className="text-sm text-mud">الفرشاة</span>
        <div role="radiogroup" aria-label="نوع التلف" className="flex flex-wrap gap-1.5">
          {damageTypes.map((type) => (
            <Button
              key={type}
              type="button"
              role="radio"
              variant="segment"
              size="sm"
              aria-checked={brush.damage_type === type}
              onClick={() => onBrush({ ...brush, damage_type: type })}
            >
              <span aria-hidden className="size-3 rounded-xs" style={{ background: colorFor(type) }} />
              {damageTypeAr[type] ?? type}
            </Button>
          ))}
          <Button
            type="button"
            role="radio"
            variant="segment"
            size="sm"
            aria-checked={erasing}
            onClick={() => onBrush({ ...brush, damage_type: "none" })}
            className="border border-dashed border-mud/60"
          >
            ممحاة: سليمة
          </Button>
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div role="radiogroup" aria-label="الخطورة" className={`flex items-center gap-1 ${erasing ? "opacity-40" : ""}`}>
          <span className="me-2 text-sm text-mud">الخطورة</span>
          {SEVERITIES.map((severity) => (
            <Button
              key={severity}
              type="button"
              role="radio"
              variant="segment"
              size="sm"
              aria-checked={brush.severity === severity}
              disabled={erasing}
              onClick={() => onBrush({ ...brush, severity })}
            >
              {severityAr[severity]}
            </Button>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button type="button" variant="ghost" size="sm" onClick={onUndo} disabled={!canUndo} aria-keyshortcuts="Control+Z">
            تراجع
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={onRedo}
            disabled={!canRedo}
            aria-keyshortcuts="Control+Shift+Z"
          >
            إعادة
          </Button>
          <Button type="button" variant="outline" onClick={onSave} disabled={busy || pendingCount === 0}>
            {busy ? "نحفظ…" : pendingCount > 0 ? `احفظ ${countAr(pendingCount, corrections)}` : "احفظ التصحيحات"}
          </Button>
          <AlertDialog open={confirming} onOpenChange={setConfirming}>
            <AlertDialogTrigger asChild>
              <Button
                type="button"
                disabled={approveBlocked}
                aria-describedby={approveBlocked && !busy ? "grid-approve-reason" : undefined}
              >
                اعتمد المخطط
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>اعتماد المخطط</AlertDialogTitle>
                <AlertDialogDescription>يُجمَّد المخطط بعد الاعتماد، ولا يمكن التعديل بعدها.</AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogAction onClick={onApprove}>اعتمد</AlertDialogAction>
                <AlertDialogCancel>إلغاء</AlertDialogCancel>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </div>
      {!busy && approveBlocked && (
        <p id="grid-approve-reason" className="text-xs text-mud">
          {!fieldInspected
            ? "الاعتماد متاح بعد تسجيل الفحص الميداني."
            : unsaved > 0
              ? "احفظ التعديلات أولًا ثم اعتمد."
              : "راجع العناصر منخفضة الثقة في وضع «عناصر التلف بالمسرد» قبل الاعتماد."}
        </p>
      )}
      <p className="text-xs text-mud">
        اسحب على الخلايا لتلوينها، أو تنقّل بالأسهم واضغط زر المسافة.{" "}
        <kbd dir="ltr" className="rounded-xs bg-muted px-1">
          Ctrl+Z
        </kbd>{" "}
        للتراجع.
      </p>
    </section>
  );
}
