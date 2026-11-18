"use client";

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
  onSave,
  onDiscard,
}: Props) {
  const entry = glossary.find((g) => g.damage_type === draft.damage_type);

  function pickType(damageType: string) {
    const next = glossary.find((g) => g.damage_type === damageType);
    onDraft({ ...draft, damage_type: damageType, damage_class: next?.classes[0] ?? null });
    if (next && tool !== "select") onTool(next.geometry);
  }

  return (
    <section aria-label="أدوات رسم عناصر التلف" className="no-print flex flex-col gap-3 rounded-xl bg-white/75 p-3">
      <div className="flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-mud">نوع التلف من المسرد</span>
          <select
            value={draft.damage_type}
            onChange={(e) => pickType(e.target.value)}
            className="min-h-11 rounded-lg border border-clay/50 bg-white px-2"
          >
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
          </select>
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
        <div role="group" aria-label="الأداة" className="flex gap-1 rounded-full bg-sand p-1">
          <button
            type="button"
            aria-pressed={tool === "select"}
            onClick={() => onTool("select")}
            className={`min-h-9 rounded-full px-3 text-sm ${tool === "select" ? "bg-ink text-sand" : "hover:bg-clay/20"}`}
          >
            اختيار
          </button>
          <button
            type="button"
            aria-pressed={tool !== "select"}
            onClick={() => entry && onTool(entry.geometry)}
            className={`min-h-9 rounded-full px-3 text-sm ${tool !== "select" ? "bg-ink text-sand" : "hover:bg-clay/20"}`}
          >
            ارسم {entry ? geometryAr[entry.geometry] : ""}
          </button>
        </div>
        {entry && <p className="text-xs text-mud">يُقاس: {entry.measure_ar}</p>}
      </div>

      {selected && (
        <div className="flex flex-wrap items-end gap-3 border-t border-clay/30 pt-3">
          <p className="w-full text-sm font-bold">
            تعديل <bdi>{selected.id}</bdi> في <bdi>{selected.location}</bdi>
          </p>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-mud">النوع</span>
            <select
              value={selected.damage_type}
              onChange={(e) => {
                const next = glossary.find((g) => g.damage_type === e.target.value);
                onChangeSelected({ ...shapeOf(selected), damage_type: e.target.value, damage_class: next?.classes[0] ?? null });
              }}
              className="min-h-11 rounded-lg border border-clay/50 bg-white px-2"
            >
              {glossary
                .filter((g) => g.geometry === selected.geometry)
                .map((g) => (
                  <option key={g.damage_type} value={g.damage_type}>
                    {g.name_ar}
                  </option>
                ))}
            </select>
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
            <button
              type="button"
              onClick={() => onChangeSelected(shapeOf(selected))}
              className="min-h-11 rounded-full bg-ink px-4 text-sm font-bold text-sand"
            >
              أكّد العنصر كما هو
            </button>
          )}
          <button
            type="button"
            onClick={onDeleteSelected}
            className="min-h-11 rounded-full border border-urgent px-4 text-sm text-urgent hover:bg-urgent hover:text-white"
          >
            احذف العنصر
          </button>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-3 border-t border-clay/30 pt-3">
        <button
          type="button"
          onClick={onSave}
          disabled={busy || pendingCount === 0}
          className="min-h-11 rounded-full bg-sadu px-5 text-sm font-bold text-sand disabled:opacity-50"
        >
          {busy ? "يُحفظ…" : `احفظ التعديلات (${pendingCount.toLocaleString("ar-SA")})`}
        </button>
        {pendingCount > 0 && (
          <button type="button" onClick={onDiscard} className="text-sm underline">
            تراجع عن كل التعديلات
          </button>
        )}
        <p className="text-xs text-mud">كل تعديل يُحفظ في سجل التصحيحات باسمك ووقته.</p>
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
      <select value={value} onChange={(e) => onChange(e.target.value)} className="min-h-11 rounded-lg border border-clay/50 bg-white px-2">
        {SEVERITIES.map((s) => (
          <option key={s} value={s}>
            {severityAr[s]}
          </option>
        ))}
      </select>
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
      <select
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value || null)}
        className="min-h-11 rounded-lg border border-clay/50 bg-white px-2"
      >
        <option value="">غير محددة</option>
        {classes.map((c) => (
          <option key={c} value={c}>
            {classAr[c] ?? c}
          </option>
        ))}
      </select>
    </label>
  );
}
