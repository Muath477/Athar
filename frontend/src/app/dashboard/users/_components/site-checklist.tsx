"use client";

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
  function toggle(siteId: string, checked: boolean) {
    onChange(checked ? [...selected, siteId] : selected.filter((id) => id !== siteId));
  }

  return (
    <fieldset className="flex flex-col gap-1" disabled={disabled}>
      <legend className="mb-1">المواقع المسموحة</legend>
      <p className="text-sm text-mud">اترك المواقع كلها دون تحديد ليرى الحساب جميع المواقع.</p>
      <ul className="flex flex-wrap gap-x-4">
        {sites.map((site) => (
          <li key={site.id}>
            <label className="inline-flex min-h-11 items-center gap-2">
              <input
                type="checkbox"
                checked={selected.includes(site.id)}
                onChange={(e) => toggle(site.id, e.target.checked)}
                className="size-5 accent-sadu"
              />
              {site.name_ar}
            </label>
          </li>
        ))}
      </ul>
    </fieldset>
  );
}
