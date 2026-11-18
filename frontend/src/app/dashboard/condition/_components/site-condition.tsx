"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { ApiError, type Site, can, request, roleAr } from "@/lib/api";
import { colorFor } from "@/lib/damage-palette";
import { damageTypeAr } from "@/lib/labels";
import { type SiteCondition, getSiteCondition, setFieldPhotography } from "@/lib/maps";
import { useMe } from "@/lib/use-me";

const STATUS_AR = { draft: "بانتظار الاعتماد", approved: "معتمد", not_surveyed: "لم يُمسح" } as const;

const PERMISSIONS_AR: Record<string, string> = {
  read: "الاطلاع",
  survey: "التصوير والفحص",
  review: "المراجعة والاعتماد",
  manage_site: "إدارة الموقع",
  administer: "إدارة النظام",
};

function dateAr(value: string | null): string {
  return value ? new Date(value).toLocaleDateString("ar-SA", { day: "numeric", month: "short", year: "numeric" }) : "—";
}

export function SiteConditionView() {
  const me = useMe();
  const router = useRouter();
  const params = useSearchParams();
  const [sites, setSites] = useState<Site[] | null>(null);
  const [condition, setCondition] = useState<SiteCondition | null>(null);
  const [roles, setRoles] = useState<{ role: string; permissions: string[] }[]>([]);
  const [error, setError] = useState<string | null>(null);
  const siteId = params.get("site") ?? (sites?.find((s) => s.facades.length > 0) ?? sites?.[0])?.id ?? null;

  useEffect(() => {
    if (!me) return;
    request<Site[]>("/sites").then(setSites, () => setError("تعذر تحميل المواقع."));
    request<{ role: string; permissions: string[] }[]>("/auth/roles").then(setRoles, () => setRoles([]));
  }, [me]);

  const load = useCallback(
    (id: string) =>
      getSiteCondition(id).then(setCondition, (e) =>
        setError(e instanceof ApiError ? e.message : "تعذر تحميل حالة الموقع."),
      ),
    [],
  );

  useEffect(() => {
    if (siteId) load(siteId);
  }, [siteId, load]);

  if (error) return <p role="alert" className="pt-6">{error}</p>;
  if (!me || !sites || !condition) return <p className="pt-6">…</p>;

  const manager = can(me, "manage_site");

  async function togglePermit() {
    if (!condition) return;
    await setFieldPhotography(condition.site_id, !condition.field_photography_permitted);
    await load(condition.site_id);
  }

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex flex-col gap-1">
          <p className="text-sm text-mud">ملخص مدير الموقع · {roleAr[me.role]}</p>
          <h1 className="text-3xl font-bold leading-tight">حالة {condition.name_ar}</h1>
          <p className="text-sm text-mud">أُعد في {dateAr(condition.generated_at)} من آخر مسح لكل جدار.</p>
        </div>
        <div className="no-print flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-mud">الموقع</span>
            <select
              value={condition.site_id}
              onChange={(e) => router.replace(`/dashboard/condition?site=${e.target.value}`)}
              className="min-h-11 rounded-lg border border-clay/50 bg-white px-2"
            >
              {sites.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name_ar}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            onClick={() => window.print()}
            className="min-h-11 rounded-full bg-sadu px-5 text-sm font-bold text-sand"
          >
            اطبع التقرير الدوري
          </button>
        </div>
      </header>

      <ul className="grid gap-3 sm:grid-cols-4" aria-label="أرقام الموقع">
        <Fact value={condition.urgent} label="عنصر تلف عاجل" tone={condition.urgent ? "urgent" : undefined} />
        <Fact value={condition.awaiting_approval} label="جدار بانتظار اعتماد المختص" />
        <Fact value={condition.walls_due} label="جدار يحتاج مسحًا" />
        <li className="flex flex-col gap-1 rounded-xl bg-white/75 p-3">
          <span className="text-lg font-bold">
            {condition.field_photography_permitted ? "مسموح بتصريح" : "غير مسموح"}
          </span>
          <span className="text-sm text-mud">تصوير الزوار الميداني</span>
          {manager && (
            <button type="button" onClick={togglePermit} className="no-print w-fit text-sm font-bold text-sadu underline">
              {condition.field_photography_permitted ? "أوقف التصريح" : "سجّل تصريح الهيئة"}
            </button>
          )}
        </li>
      </ul>

      <section aria-labelledby="walls-title" className="flex flex-col gap-2">
        <h2 id="walls-title" className="text-lg font-bold">
          الجدران مرتبة حسب الأولوية
        </h2>
        {condition.walls.length === 0 ? (
          <p className="rounded-xl bg-white/75 p-3 text-mud">
            لا جدران مسجلة لهذا الموقع بعد. ارسم مخطط جدار أو أضف واجهات الموقع في حزمة المنطقة.
          </p>
        ) : (
        <div className="overflow-x-auto rounded-xl bg-white/75">
          <table className="w-full text-sm">
            <thead className="text-mud">
              <tr className="border-b border-clay/30">
                <th className="p-2 text-start font-normal">الجدار</th>
                <th className="p-2 text-start font-normal">الحالة</th>
                <th className="p-2 text-start font-normal">آخر مسح</th>
                <th className="p-2 text-start font-normal">الفحص الميداني</th>
                <th className="p-2 text-start font-normal">العناصر</th>
                <th className="p-2 text-start font-normal">عاجل</th>
                <th className="p-2 text-start font-normal">ثقة منخفضة</th>
                <th className="p-2 text-start font-normal">المساحة</th>
                <th className="p-2 text-start font-normal">إشراف مختص</th>
              </tr>
            </thead>
            <tbody>
              {condition.walls.map((wall) => (
                <tr key={wall.facade_id ?? wall.name_ar} className="border-b border-clay/20 last:border-0">
                  <td className="p-2 font-bold">
                    {wall.map_id ? (
                      <Link href={`/dashboard/maps/${wall.map_id}`} className="hover:text-sadu">
                        {wall.name_ar}
                      </Link>
                    ) : (
                      wall.name_ar
                    )}
                    {wall.survey_due && <span className="ms-2 text-xs text-moderate">مسح مستحق</span>}
                  </td>
                  <td className="p-2">{STATUS_AR[wall.status]}</td>
                  <td className="p-2 tabular-nums">{dateAr(wall.surveyed_at)}</td>
                  <td className="p-2 tabular-nums">{dateAr(wall.field_inspected_at)}</td>
                  <td className="p-2 tabular-nums">{wall.elements.toLocaleString("ar-SA")}</td>
                  <td className={`p-2 tabular-nums ${wall.urgent ? "font-bold text-urgent" : ""}`}>
                    {wall.urgent.toLocaleString("ar-SA")}
                  </td>
                  <td className="p-2 tabular-nums">{wall.needs_review.toLocaleString("ar-SA")}</td>
                  <td className="p-2 tabular-nums">
                    {wall.damaged_area_m2.toLocaleString("ar-SA", { maximumFractionDigits: 1 })} م²
                  </td>
                  <td className="p-2">{wall.needs_specialist ? "نعم" : "لا"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        )}
      </section>

      <div className="grid gap-5 lg:grid-cols-2">
        <section aria-labelledby="types-title" className="flex flex-col gap-2">
          <h2 id="types-title" className="text-lg font-bold">
            التلف على مستوى الموقع
          </h2>
          {condition.totals.length === 0 ? (
            <p className="text-mud">لا تلف مسجل بعد.</p>
          ) : (
            <ul className="flex flex-col gap-1.5 rounded-xl bg-white/75 p-3 text-sm">
              {condition.totals.map((t) => (
                <li key={t.damage_type} className="flex items-center gap-2">
                  <span className="inline-block size-3 rounded-sm border border-ink/20" style={{ background: colorFor(t.damage_type) }} />
                  <span className="flex-1">{damageTypeAr[t.damage_type] ?? t.damage_type}</span>
                  <span className="tabular-nums">{t.elements.toLocaleString("ar-SA")} عنصر</span>
                  {t.urgent > 0 && <span className="font-bold text-urgent">{t.urgent.toLocaleString("ar-SA")} عاجل</span>}
                </li>
              ))}
            </ul>
          )}
        </section>
        <section aria-labelledby="materials-title" className="flex flex-col gap-2">
          <h2 id="materials-title" className="text-lg font-bold">
            مواد المعالجات المعتمدة
          </h2>
          {condition.materials.length === 0 ? (
            <p className="text-mud">لا معالجات معتمدة بعد. الكميات تظهر بعد اعتماد المختص.</p>
          ) : (
            <ul className="flex flex-col gap-1 rounded-xl bg-white/75 p-3 text-sm">
              {condition.materials.map((m) => (
                <li key={`${m.name_ar}-${m.unit_ar}`} className="flex justify-between gap-2">
                  <span>{m.name_ar}</span>
                  <span className="tabular-nums">
                    {m.quantity.toLocaleString("ar-SA")} {m.unit_ar}
                  </span>
                </li>
              ))}
            </ul>
          )}
          {!condition.catalog_reviewed && (
            <p className="text-xs text-mud">مكتبة المعالجات مسودة حتى يعتمدها مختص ترميم من الجهة.</p>
          )}
        </section>
      </div>

      {roles.length > 0 && (
        <section aria-labelledby="roles-title" className="no-print flex flex-col gap-2">
          <h2 id="roles-title" className="text-lg font-bold">
            من يفعل ماذا
          </h2>
          <ul className="grid gap-2 text-sm sm:grid-cols-2 lg:grid-cols-4">
            {roles.map((r) => (
              <li key={r.role} className="rounded-xl bg-white/75 p-3">
                <p className="font-bold">{roleAr[r.role as keyof typeof roleAr] ?? r.role}</p>
                <p className="text-mud">{Object.keys(PERMISSIONS_AR)
                    .filter((p) => r.permissions.includes(p))
                    .map((p) => PERMISSIONS_AR[p])
                    .join("، ")}</p>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

function Fact({ value, label, tone }: { value: number; label: string; tone?: "urgent" }) {
  return (
    <li className="flex flex-col gap-1 rounded-xl bg-white/75 p-3">
      <span className={`text-2xl font-bold tabular-nums ${tone === "urgent" ? "text-urgent" : ""}`}>
        {value.toLocaleString("ar-SA")}
      </span>
      <span className="text-sm text-mud">{label}</span>
    </li>
  );
}
