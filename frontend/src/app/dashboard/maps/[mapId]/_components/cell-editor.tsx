"use client";

import { type FormEvent } from "react";
import { damageTypeAr, severityAr } from "@/lib/labels";
import type { CellCorrection, MapCell } from "@/lib/maps";

const SEVERITIES = ["watch", "moderate", "urgent"];

export function CellEditor({
  cell,
  current,
  damageTypes,
  onApply,
  onCancel,
}: {
  cell: string;
  current: MapCell | null;
  damageTypes: string[];
  onApply: (correction: CellCorrection) => void;
  onCancel: () => void;
}) {
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    onApply({ cell, damage_type: String(form.get("damage_type")), severity: String(form.get("severity")) });
  }

  return (
    <form onSubmit={submit} className="no-print flex flex-col gap-3 rounded-xl bg-white/80 p-3">
      <h2 className="font-bold">الخلية {cell}</h2>
      <label className="flex flex-col gap-1 text-sm">
        <span>نوع التلف</span>
        <select name="damage_type" defaultValue={current?.damage_type ?? "none"} className="rounded border p-1">
          <option value="none">سليمة</option>
          {damageTypes.map((type) => (
            <option key={type} value={type}>
              {damageTypeAr[type] ?? type}
            </option>
          ))}
        </select>
      </label>
      <fieldset className="flex flex-wrap gap-3 text-sm">
        <legend className="mb-1">الخطورة</legend>
        {SEVERITIES.map((severity) => (
          <label key={severity} className="flex items-center gap-1">
            <input type="radio" name="severity" value={severity} defaultChecked={(current?.severity ?? "watch") === severity} />
            {severityAr[severity]}
          </label>
        ))}
      </fieldset>
      <div className="flex gap-2">
        <button type="submit" className="rounded-full bg-ink px-4 py-1 text-sand">
          تطبيق
        </button>
        <button type="button" onClick={onCancel} className="rounded-full border px-4 py-1">
          إلغاء
        </button>
      </div>
    </form>
  );
}
