"use client";

import { useId } from "react";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import type { Site } from "@/lib/api";

export function SiteChecklist({
  sites,
  selected,
  onChange,
  disabled = false,
}: {
  sites: Site[];
  selected: string[];
  onChange: (siteIds: string[]) => void;
  disabled?: boolean;
}) {
  const idPrefix = useId();

  function toggle(siteId: string, checked: boolean) {
    onChange(checked ? [...selected, siteId] : selected.filter((id) => id !== siteId));
  }

  return (
    <fieldset className="flex flex-col gap-1" disabled={disabled}>
      <legend className="mb-1 text-sm text-mud">المواقع المسموحة</legend>
      <p className="text-xs text-mud">اترك المواقع كلها دون تحديد ليرى الحساب جميع المواقع.</p>
      <ul className="flex flex-wrap gap-x-5">
        {sites.map((site) => {
          const checkboxId = `${idPrefix}-${site.id}`;
          return (
            <li key={site.id} className="flex min-h-11 items-center gap-2">
              <Checkbox
                id={checkboxId}
                checked={selected.includes(site.id)}
                disabled={disabled}
                onCheckedChange={(checked) => toggle(site.id, checked === true)}
              />
              <Label htmlFor={checkboxId} className="text-base text-ink">
                {site.name_ar}
              </Label>
            </li>
          );
        })}
      </ul>
    </fieldset>
  );
}
