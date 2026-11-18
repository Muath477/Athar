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
import { NativeSelect } from "@/components/ui/native-select";
import { classAr, classKindAr, geometryAr } from "@/lib/elements";
import { severityAr } from "@/lib/labels";
import type { ElementShape, GlossaryEntry, MapElement } from "@/lib/maps";
import type { Tool } from "./element-canvas";

const SEVERITIES = ["watch", "moderate", "urgent"] as const;

type Props = {
  glossary: GlossaryEntry[];
  tool: Tool;
  onTool: (tool: Tool) => void;
  draft: ElementShape;
  onDraft: (draft: ElementShape) => void;
  selected: MapElement | null;
  onChangeSelected: (shape: ElementShape) => void;
  onDeleteSelected: () => void;
  pendingCount: number;
  busy: boolean;
  canUndo: boolean;
  canRedo: boolean;
  onUndo: () => void;
  onRedo: () => void;
  onSave: () => void;
  onDiscard: () => void;
};

export function ElementTools({
  glossary,
  tool,
  onTool,
  draft,
  onDraft,
  selected,
  onChangeSelected,
  onDeleteSelected,
  pendingCount,
  busy,
  canUndo,
  canRedo,
  onUndo,
  onRedo,
  onSave,
  onDiscard,
}: Props) {
  const [confirmingDiscard, setConfirmingDiscard] = useState(false);
  if (confirmingDiscard && pendingCount === 0) setConfirmingDiscard(false);
  const entry = glossary.find((g) => g.damage_type === draft.damage_type);

  function pickType(damageType: string) {
    const next = glossary.find((g) => g.damage_type === damageType);
    onDraft({ ...draft, damage_type: damageType, damage_class: next?.classes[0] ?? null });
    if (next && tool !== "select") onTool(next.geometry);
  }

  return (
    <section aria-label="أدوات رسم عناصر التلف" className="no-print flex flex-col gap-3 rounded-sm border border-line bg-white p-3">
      <div className="flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-mud">نوع التلف من المسرد</span>
          <NativeSelect value={draft.damage_type} onChange={(e) => pickType(e.target.value)}>
            <optgroup label="المسرد الموحد">
              {glossary.filter((g) => g.core).map((g) => (
                <option key={g.damage_type} value={g.damage_type}>
                  {g.name_ar} · {geometryAr[g.geometry]}
                </option>
              ))}
            </optgroup>
            <optgroup label="أنواع إضافية">
              {glossary.filter((g) => !g.core).map((g) => (
                <option key={g.damage_type} value={g.damage_type}>
                  {g.name_ar} · {geometryAr[g.geometry]}
                </option>
              ))}
            </optgroup>
          </NativeSelect>
        </label>
        <SeverityPicker value={draft.severity} onChange={(severity) => onDraft({ ...draft, severity })} />
        {entry?.class_kind && (
          <ClassPicker
            label={classKindAr[entry.class_kind]}
            classes={entry.classes}
            value={draft.damage_class}
            onChange={(damage_class) => onDraft({ ...draft, damage_class })}
          />
        )}
        <div role="group" aria-label="الأداة" className="flex gap-1 rounded-sm border border-line p-0.5">
          <Button
            type="button"
            variant="segment"
            size="sm"
            aria-pressed={tool === "select"}
            onClick={() => onTool("select")}
          >
            اختيار
          </Button>
          <Button
            type="button"
            variant="segment"
            size="sm"
            aria-pressed={tool !== "select"}
            onClick={() => entry && onTool(entry.geometry)}
          >
            ارسم {entry ? geometryAr[entry.geometry] : ""}
          </Button>
        </div>
        {entry && <p className="text-xs text-mud">يُقاس: {entry.measure_ar}</p>}
      </div>

      {selected && (
        <div className="flex flex-wrap items-end gap-3 border-t border-line pt-3">
          <p className="w-full text-sm font-bold">
            تعديل <bdi>{selected.id}</bdi> في <bdi>{selected.location}</bdi>
          </p>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-mud">النوع</span>
            <NativeSelect
              value={selected.damage_type}
              onChange={(e) => {
                const next = glossary.find((g) => g.damage_type === e.target.value);
                onChangeSelected({ ...shapeOf(selected), damage_type: e.target.value, damage_class: next?.classes[0] ?? null });
              }}
            >
              {glossary
                .filter((g) => g.geometry === selected.geometry)
                .map((g) => (
                  <option key={g.damage_type} value={g.damage_type}>
                    {g.name_ar}
                  </option>
                ))}
            </NativeSelect>
          </label>
          <SeverityPicker
            value={selected.severity}
            onChange={(severity) => onChangeSelected({ ...shapeOf(selected), severity })}
          />
          {(() => {
            const selectedEntry = glossary.find((g) => g.damage_type === selected.damage_type);
            return selectedEntry?.class_kind ? (
              <ClassPicker
                label={classKindAr[selectedEntry.class_kind]}
                classes={selectedEntry.classes}
                value={selected.damage_class}
                onChange={(damage_class) => onChangeSelected({ ...shapeOf(selected), damage_class })}
              />
            ) : null;
          })()}
          {selected.needs_review && (
            <Button type="button" variant="outline" onClick={() => onChangeSelected(shapeOf(selected))}>
              أكّد العنصر كما هو
            </Button>
          )}
          <Button type="button" variant="destructive-outline" onClick={onDeleteSelected}>
            احذف العنصر
          </Button>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-3 border-t border-line pt-3">
        <div role="group" aria-label="التراجع والإعادة" className="flex gap-1">
          <Button type="button" variant="ghost" onClick={onUndo} disabled={!canUndo} aria-keyshortcuts="Control+Z">
            تراجع
          </Button>
          <Button
            type="button"
            variant="ghost"
            onClick={onRedo}
            disabled={!canRedo}
            aria-keyshortcuts="Control+Shift+Z"
          >
            إعادة
          </Button>
        </div>
        <Button
          type="button"
          variant={pendingCount > 0 ? "default" : "outline"}
          onClick={onSave}
          disabled={busy || pendingCount === 0}
        >
          {busy ? "يُحفظ…" : `احفظ التعديلات (${pendingCount.toLocaleString("ar-SA")})`}
        </Button>
        {pendingCount > 0 && (
          <AlertDialog open={confirmingDiscard} onOpenChange={setConfirmingDiscard}>
            <AlertDialogTrigger asChild>
              <Button type="button" variant="link" className="font-normal text-ink">
                تراجع عن كل التعديلات
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>إلغاء التعديلات غير المحفوظة</AlertDialogTitle>
                <AlertDialogDescription>تُلغى كل التعديلات غير المحفوظة. متأكد؟</AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogAction variant="destructive" onClick={onDiscard}>
                  ألغِ التعديلات
                </AlertDialogAction>
                <AlertDialogCancel>أبقِها</AlertDialogCancel>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        )}
        <p className="text-xs text-mud">
          كل تعديل يُحفظ في سجل التصحيحات باسمك ووقته. للتراجع <kbd dir="ltr" className="rounded-xs bg-muted px-1">Ctrl+Z</kbd>.
        </p>
      </div>
    </section>
  );
}

function shapeOf(element: MapElement): ElementShape {
  return {
    damage_type: element.damage_type,
    points: element.points,
    severity: element.severity,
    damage_class: element.damage_class,
  };
}

function SeverityPicker({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      <span className="text-mud">الشدة</span>
      <NativeSelect value={value} onChange={(e) => onChange(e.target.value)}>
        {SEVERITIES.map((s) => (
          <option key={s} value={s}>
            {severityAr[s]}
          </option>
        ))}
      </NativeSelect>
    </label>
  );
}

function ClassPicker({
  label,
  classes,
  value,
  onChange,
}: {
  label: string;
  classes: string[];
  value: string | null;
  onChange: (value: string | null) => void;
}) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      <span className="text-mud">{label}</span>
      <NativeSelect value={value ?? ""} onChange={(e) => onChange(e.target.value || null)}>
        <option value="">غير محددة</option>
        {classes.map((c) => (
          <option key={c} value={c}>
            {classAr[c] ?? c}
          </option>
        ))}
      </NativeSelect>
    </label>
  );
}
