"use client";

import { useId } from "react";
import { type Role, roleAr } from "@/lib/api";
import { type RoleMatrixRow, permissionAr } from "@/lib/governance";

export const FIELD_CLASS = "min-h-11 rounded-lg border border-mud/60 bg-white px-3 disabled:opacity-50";

export function RolePicker({
  matrix,
  value,
  onChange,
  disabled = false,
}: {
  matrix: RoleMatrixRow[];
  value: Role;
  onChange: (role: Role) => void;
  disabled?: boolean;
}) {
  const descriptionId = useId();
  const permissions = matrix.find((row) => row.role === value)?.permissions ?? [];

  return (
    <div className="flex flex-col gap-1">
      <label className="flex flex-col gap-1">
        الدور
        <select
          value={value}
          onChange={(e) => onChange(e.target.value as Role)}
          disabled={disabled}
          aria-describedby={descriptionId}
          className={FIELD_CLASS}
        >
          {matrix.map((row) => (
            <option key={row.role} value={row.role}>
              {roleAr[row.role]}
            </option>
          ))}
        </select>
      </label>
      <p id={descriptionId} className="text-sm leading-relaxed text-mud">
        يستطيع: {permissions.map((p) => permissionAr[p]).join("، ")}.
      </p>
    </div>
  );
}

export function RoleMatrix({ matrix }: { matrix: RoleMatrixRow[] }) {
  return (
    <details className="rounded-xl bg-white/60 p-3">
      <summary className="min-h-11 cursor-pointer content-center font-bold">ما يستطيعه كل دور</summary>
      <ul className="mt-2 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {matrix.map((row) => (
          <li key={row.role} className="flex flex-col gap-1 rounded-lg bg-white/75 p-3">
            <span className="font-bold">{roleAr[row.role]}</span>
            <ul className="list-inside list-disc text-sm leading-relaxed text-mud">
              {row.permissions.map((p) => (
                <li key={p}>{permissionAr[p]}</li>
              ))}
            </ul>
          </li>
        ))}
      </ul>
    </details>
  );
}
