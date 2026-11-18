"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useState } from "react";
import { EvidencePanel } from "@/components/evidence-panel";
import { type Coverage, type Finding, request, type Site } from "@/lib/api";
import { damageTypeAr, findingLabelAr, severityAr } from "@/lib/labels";
import { useMe } from "@/lib/use-me";

const SiteModel = dynamic(() => import("./site-model").then((m) => m.SiteModel), {
  ssr: false,
  loading: () => <div className="h-full animate-pulse rounded-xl bg-clay/20" />,
});

export function DashboardView() {
  const me = useMe();
  const [sites, setSites] = useState<Site[]>([]);
  const [siteId, setSiteId] = useState<string | null>(null);
  const [pins, setPins] = useState<Finding[]>([]);
  const [coverage, setCoverage] = useState<Coverage[]>([]);
  const [selected, setSelected] = useState<Finding | null>(null);

  useEffect(() => {
    if (!me) return;
    request<Site[]>("/sites").then((list) => {
      setSites(list);
      setSiteId((current) => current ?? list[0]?.id ?? null);
    });
  }, [me]);

  const refresh = useCallback(
    (id: string) =>
      Promise.all([request<Finding[]>(`/sites/${id}/pins`), request<Coverage[]>(`/sites/${id}/coverage`)]).then(
        ([findings, facadeCoverage]) => {
          setPins(findings);
          setCoverage(facadeCoverage);
        },
      ),
    [],
  );

  useEffect(() => {
    if (siteId) refresh(siteId);
  }, [siteId, refresh]);

  async function select(findingId: string) {
    setSelected(await request<Finding>(`/findings/${findingId}`));
  }

  async function dispatch(facadeId: string) {
    await request("/missions", { method: "POST", body: JSON.stringify({ facade_id: facadeId }) });
    if (siteId) await refresh(siteId);
  }

  const site = sites.find((s) => s.id === siteId);
  if (!me) return <p className="pt-6">…</p>;

  return (
    <div className="flex flex-col gap-4 pt-2">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <select
          value={siteId ?? ""}
          onChange={(e) => setSiteId(e.target.value)}
          className="rounded-lg border bg-white/70 p-2"
          aria-label="الموقع"
        >
          {sites.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name_ar}
            </option>
          ))}
        </select>

      </div>

      <div className="grid gap-4 lg:grid-cols-[2fr_1fr]">
        <div className="h-[420px]">
          {site && <SiteModel facades={site.facades} findings={pins} selectedId={selected?.id ?? null} onSelect={select} />}
        </div>
        <section className="flex flex-col gap-2">
          <h2 className="font-bold">الأضرار المنشورة ({pins.length})</h2>
          <ul className="flex max-h-[380px] flex-col gap-2 overflow-y-auto">
            {pins.map((f) => (
              <li key={f.id}>
                <button onClick={() => select(f.id)} className="w-full rounded-lg bg-white/70 p-2 text-start text-sm">
                  {damageTypeAr[f.damage_type] ?? f.damage_type} · {severityAr[f.severity]} · {findingLabelAr[f.label]}
                </button>
              </li>
            ))}
          </ul>
        </section>
      </div>

      {selected && <EvidencePanel finding={selected} onClose={() => setSelected(null)} />}

      <section className="flex flex-col gap-2">
        <h2 className="font-bold">تغطية الواجهات</h2>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-start">
              <th className="text-start">الواجهة</th>
              <th className="text-start">آخر صورة صالحة</th>
              <th className="text-start">مهمة</th>
            </tr>
          </thead>
          <tbody>
            {coverage.map((c) => (
              <tr key={c.facade_id} className="border-t border-clay/30">
                <td className="py-1.5">{c.name_ar}</td>
                <td>{daysAgo(c.days_since_last_photo)}</td>
                <td>
                  {c.open_mission_id ? (
                    "مفتوحة"
                  ) : (
                    <button onClick={() => dispatch(c.facade_id)} className="underline">
                      اطلب صورة
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

function daysAgo(days: number | null): string {
  if (days === null) return "لا توجد";
  if (days === 0) return "اليوم";
  return `قبل ${days.toLocaleString("ar-SA")} يوم`;
}
