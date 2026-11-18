"use client";

import { useId } from "react";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";
import { type Role, roleAr } from "@/lib/api";
import { type RoleMatrixRow, permissionAr } from "@/lib/governance";

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
  const selectId = useId();
  const descriptionId = useId();
  const permissions = matrix.find((row) => row.role === value)?.permissions ?? [];

  return (
    <div className="flex w-full flex-col gap-1.5">
      <Label htmlFor={selectId}>الدور</Label>
      <NativeSelect
        id={selectId}
        value={value}
        onChange={(e) => onChange(e.target.value as Role)}
        disabled={disabled}
        aria-describedby={descriptionId}
      >
        {matrix.map((row) => (
          <option key={row.role} value={row.role}>
            {roleAr[row.role]}
          </option>
        ))}
      </NativeSelect>
      <p id={descriptionId} className="text-xs leading-relaxed text-mud">
        يستطيع: {permissions.map((p) => permissionAr[p]).join("، ")}.
      </p>
    </div>
  );
}

export function RoleMatrix({ matrix }: { matrix: RoleMatrixRow[] }) {
  return (
    <details className="border-y border-line">
      <summary className="flex min-h-11 cursor-pointer items-center font-bold">ما يستطيعه كل دور</summary>
      <dl className="grid gap-x-6 gap-y-3 pb-4 sm:grid-cols-2 lg:grid-cols-3">
        {matrix.map((row) => (
          <div key={row.role} className="flex flex-col gap-1 border-t border-line pt-2">
            <dt className="font-bold">{roleAr[row.role]}</dt>
            <dd>
              <ul className="list-inside list-disc text-sm leading-relaxed text-mud">
                {row.permissions.map((p) => (
                  <li key={p}>{permissionAr[p]}</li>
                ))}
              </ul>
            </dd>
          </div>
        ))}
      </dl>
    </details>
  );
}
