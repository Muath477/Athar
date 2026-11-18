"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { TriangleAlertIcon } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { RetryAlert } from "@/app/_components/page-status";
import { MarginNote } from "@/components/brand/margin-note";
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
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { NativeSelect } from "@/components/ui/native-select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ApiError, type Site, can, conditionExportUrl, request, roleAr } from "@/lib/api";
import { colorFor } from "@/lib/damage-palette";
import { damageTypeAr } from "@/lib/labels";
import { type SiteCondition, type WallCondition, getSiteCondition, setFieldPhotography } from "@/lib/maps";
import { type Forms, countAr, elements, urgentElements } from "@/lib/plural";
import { useMe } from "@/lib/use-me";

const STATUS_AR = { draft: "بانتظار الاعتماد", approved: "معتمد", not_surveyed: "لم يُمسح" } as const;

const STATUS_BADGE = { draft: "outline", approved: "ink", not_surveyed: "muted" } as const;

const walls: Forms = { zero: "لا جدران", one: "جدار واحد", two: "جداران", few: "جدران", many: "جدارًا", hundred: "جدار" };

const PERMISSIONS_AR: Record<string, string> = {
  read: "الاطلاع",
  survey: "التصوير والفحص",
  review: "المراجعة والاعتماد",
  manage_site: "إدارة الموقع",
  manage_devices: "إدارة الكاميرات والأجهزة",
  export: "تصدير البيانات والتقارير",
  assistant: "استخدام مساعد أثر",
  manage_models: "إدارة النماذج والتدريب",
  administer: "إدارة النظام",
};

function dateAr(value: string | null): string {
  return value ? new Date(value).toLocaleDateString("ar-SA", { day: "numeric", month: "short", year: "numeric" }) : "—";
}

function areaM2(value: number): string {
  return `${value.toLocaleString("ar-SA", { maximumFractionDigits: 1 })} م²`;
}

export function SiteConditionView() {
  const me = useMe();
  const router = useRouter();
  const params = useSearchParams();
  const [sites, setSites] = useState<Site[] | null>(null);
  const [condition, setCondition] = useState<SiteCondition | null>(null);
  const [roles, setRoles] = useState<{ role: string; permissions: string[] }[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [permitBusy, setPermitBusy] = useState(false);
  const [permitError, setPermitError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [permitUpdated, setPermitUpdated] = useState(false);
  const siteId = params.get("site") ?? (sites?.find((s) => s.facades.length > 0) ?? sites?.[0])?.id ?? null;

  const loadSites = useCallback(
    () => request<Site[]>("/sites").then(setSites, () => setError("تعذر تحميل المواقع.")),
    [],
  );

  const load = useCallback(
    (id: string) =>
      getSiteCondition(id).then(setCondition, (e) =>
        setError(e instanceof ApiError ? e.message : "تعذر تحميل حالة الموقع."),
      ),
    [],
  );

  useEffect(() => {
    if (!me) return;
    loadSites();
    request<{ role: string; permissions: string[] }[]>("/auth/roles").then(setRoles, () => setRoles([]));
  }, [me, loadSites]);

  useEffect(() => {
    if (siteId) load(siteId);
  }, [siteId, load]);

  function retry() {
    setError(null);
    if (!sites) loadSites();
    else if (siteId) load(siteId);
  }

  if (error) return <LoadError message={error} onRetry={retry} />;
  if (!me || !sites) return <ConditionSkeleton />;
  if (sites.length === 0) {
    return (
      <div className="flex flex-col gap-4">
        <h1 className="text-3xl font-bold">حالة الموقع</h1>
        <p className="rounded-sm border border-line bg-white p-3 text-mud">لا مواقع مسجلة بعد.</p>
      </div>
    );
  }
  if (!condition) return <ConditionSkeleton />;

  const manager = can(me, "manage_site");
  const permitted = condition.field_photography_permitted;

  async function togglePermit() {
    if (!condition) return;
    setPermitBusy(true);
    setPermitError(null);
    try {
      await setFieldPhotography(condition.site_id, !condition.field_photography_permitted);
      await load(condition.site_id);
      setPermitUpdated(true);
      setConfirming(false);
    } catch (e) {
      setPermitError(e instanceof ApiError ? e.message : "تعذر تحديث التصريح. أعد المحاولة.");
    } finally {
      setPermitBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex flex-col gap-1">
          <p className="text-sm text-mud">ملخص مدير الموقع · {roleAr[me.role]}</p>
          <h1 className="text-3xl font-bold">حالة {condition.name_ar}</h1>
          <p className="text-sm text-mud">أُعد في {dateAr(condition.generated_at)} من آخر مخطط معتمد لكل جدار.</p>
        </div>
        <div className="no-print flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-mud">الموقع</span>
            <NativeSelect
              value={condition.site_id}
              onChange={(e) => {
                setConfirming(false);
                setPermitUpdated(false);
                setPermitError(null);
                router.replace(`/dashboard/condition?site=${e.target.value}`);
              }}
            >
              {sites.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name_ar}
                </option>
              ))}
            </NativeSelect>
          </label>
          <Button type="button" onClick={() => window.print()}>
            اطبع التقرير الدوري
          </Button>
          {can(me, "export") && (
            <>
              <a
                href={conditionExportUrl(condition.site_id, "pdf")}
                download
                className={buttonVariants({ variant: "outline" })}
              >
                نزّل التقرير PDF
              </a>
              <a
                href={conditionExportUrl(condition.site_id, "csv")}
                download
                className={buttonVariants({ variant: "outline" })}
              >
                نزّل الجدول CSV
              </a>
            </>
          )}
        </div>
      </header>

      <ul className="grid gap-3 sm:grid-cols-4" aria-label="أرقام الموقع">
        <li
          className={`flex flex-col gap-1 rounded-sm border bg-white p-3 sm:col-span-2 ${
            condition.urgent ? "border-urgent/50" : "border-line"
          }`}
        >
          <span className="text-sm text-mud">التلف العاجل</span>
          <span
            className={`inline-flex items-center gap-2 text-2xl font-bold tabular-nums ${condition.urgent ? "text-urgent" : ""}`}
          >
            {condition.urgent > 0 && <TriangleAlertIcon className="size-6 shrink-0" aria-hidden="true" />}
            {countAr(condition.urgent, urgentElements)}
          </span>
        </li>
        <Fact label="بانتظار اعتماد المختص" value={countAr(condition.awaiting_approval, walls)} />
        <Fact label="تحتاج مسحًا جديدًا" value={countAr(condition.walls_due, walls)} />
      </ul>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-3 rounded-sm border border-line bg-white p-3">
        <p role="status" className="min-w-0 flex-1">
          <span className="text-mud">تصوير الزوار الميداني: </span>
          <strong>{permitted ? "مسموح بتصريح" : "غير مسموح"}</strong>
          {permitUpdated && <span className="no-print text-mud"> · حُدّث التصريح.</span>}
        </p>
        {manager && (
          <AlertDialog
            open={confirming}
            onOpenChange={(open) => {
              if (permitBusy) return;
              setPermitError(null);
              if (open) setPermitUpdated(false);
              setConfirming(open);
            }}
          >
            <AlertDialogTrigger asChild>
              <Button type="button" variant="outline" className="no-print">
                {permitted ? "أوقف التصريح" : "سجّل تصريح الهيئة"}
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>{permitted ? "إيقاف تصريح التصوير" : "تسجيل تصريح الهيئة"}</AlertDialogTitle>
                <AlertDialogDescription>
                  {permitted
                    ? "سيتوقف تصوير الزوار لهذا الموقع فورًا. متأكد؟"
                    : "تُفتح مهام التصوير للزوار بعد تسجيل تصريح الهيئة. متأكد؟"}
                </AlertDialogDescription>
              </AlertDialogHeader>
              {permitError && (
                <p role="alert" className="rounded-sm border border-urgent/40 bg-urgent/5 p-3 text-sm">
                  {permitError}
                </p>
              )}
              <AlertDialogFooter>
                <AlertDialogAction
                  onClick={(event) => {
                    event.preventDefault();
                    togglePermit();
                  }}
                  disabled={permitBusy}
                  aria-busy={permitBusy}
                >
                  {permitBusy ? "نحدّث التصريح…" : "تأكيد"}
                </AlertDialogAction>
                <AlertDialogCancel disabled={permitBusy}>إلغاء</AlertDialogCancel>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        )}
      </div>

      <section aria-labelledby="walls-title" className="flex flex-col gap-2">
        <h2 id="walls-title" className="text-lg font-bold">
          الجدران مرتبة حسب الأولوية
        </h2>
        {condition.walls.length === 0 ? (
          <p className="rounded-sm border border-line bg-white p-3 text-mud">
            لا جدران مسجلة لهذا الموقع بعد. ارسم مخطط جدار أو أضف واجهات الموقع في حزمة المنطقة.
          </p>
        ) : (
          <>
            <ul className="flex flex-col gap-2 sm:hidden">
              {condition.walls.map((wall) => (
                <li
                  key={wall.facade_id ?? wall.name_ar}
                  className="flex flex-col gap-2 rounded-sm border border-line bg-white p-3 text-sm"
                >
                  <div className="flex items-start justify-between gap-3">
                    <WallName wall={wall} />
                    <StatusPill status={wall.status} />
                  </div>
                  {(wall.survey_due || wall.pending_draft_id) && (
                    <div className="flex flex-col items-start gap-2">
                      {wall.survey_due && <SurveyDue />}
                      {wall.pending_draft_id && <PendingDraft id={wall.pending_draft_id} />}
                    </div>
                  )}
                  <dl className="grid grid-cols-3 gap-2">
                    <div className="flex flex-col">
                      <dt className="text-mud">عاجل</dt>
                      <dd className={wall.urgent ? "inline-flex items-center gap-1 font-bold text-urgent" : ""}>
                        {wall.urgent > 0 && <TriangleAlertIcon className="size-4 shrink-0" aria-hidden="true" />}
                        {countAr(wall.urgent, urgentElements)}
                      </dd>
                    </div>
                    <div className="flex flex-col">
                      <dt className="text-mud">المساحة</dt>
                      <dd>
                        <bdi className="whitespace-nowrap tabular-nums">{areaM2(wall.damaged_area_m2)}</bdi>
                      </dd>
                    </div>
                    <div className="flex flex-col">
                      <dt className="text-mud">الفحص الميداني</dt>
                      <dd className="tabular-nums">{dateAr(wall.field_inspected_at)}</dd>
                    </div>
                  </dl>
                </li>
              ))}
            </ul>
            <div className="hidden sm:block">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>الجدار</TableHead>
                    <TableHead>الحالة</TableHead>
                    <TableHead>آخر مسح</TableHead>
                    <TableHead>الفحص الميداني</TableHead>
                    <TableHead>العناصر</TableHead>
                    <TableHead>عاجل</TableHead>
                    <TableHead>ثقة منخفضة</TableHead>
                    <TableHead>المساحة</TableHead>
                    <TableHead>إشراف مختص</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {condition.walls.map((wall) => (
                    <TableRow key={wall.facade_id ?? wall.name_ar}>
                      <TableCell>
                        <div className="flex flex-col items-start gap-1">
                          <WallName wall={wall} />
                          {wall.survey_due && <SurveyDue />}
                          {wall.pending_draft_id && <PendingDraft id={wall.pending_draft_id} />}
                        </div>
                      </TableCell>
                      <TableCell>
                        <StatusPill status={wall.status} />
                      </TableCell>
                      <TableCell>{dateAr(wall.surveyed_at)}</TableCell>
                      <TableCell>{dateAr(wall.field_inspected_at)}</TableCell>
                      <TableCell>{wall.elements.toLocaleString("ar-SA")}</TableCell>
                      <TableCell className={wall.urgent ? "font-bold text-urgent" : ""}>
                        <span className="inline-flex items-center gap-1">
                          {wall.urgent > 0 && <TriangleAlertIcon className="size-4 shrink-0" aria-hidden="true" />}
                          {wall.urgent.toLocaleString("ar-SA")}
                        </span>
                      </TableCell>
                      <TableCell>{wall.needs_review.toLocaleString("ar-SA")}</TableCell>
                      <TableCell>
                        <bdi className="whitespace-nowrap tabular-nums">{areaM2(wall.damaged_area_m2)}</bdi>
                      </TableCell>
                      <TableCell>{wall.needs_specialist ? "نعم" : "لا"}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </>
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
            <ul className="flex flex-col gap-1.5 rounded-sm border border-line bg-white p-3 text-sm">
              {condition.totals.map((t) => (
                <li key={t.damage_type} className="flex flex-wrap items-center gap-x-2">
                  <span
                    className="inline-block size-3 rounded-sm border border-ink/20"
                    style={{ background: colorFor(t.damage_type) }}
                  />
                  <span className="flex-1">{damageTypeAr[t.damage_type] ?? t.damage_type}</span>
                  <span>{countAr(t.elements, elements)}</span>
                  {t.urgent > 0 && (
                    <span className="inline-flex items-center gap-1 font-bold text-urgent">
                      <TriangleAlertIcon className="size-4 shrink-0" aria-hidden="true" />
                      منها {countAr(t.urgent, urgentElements)}
                    </span>
                  )}
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
            <ul className="flex flex-col gap-1 rounded-sm border border-line bg-white p-3 text-sm">
              {condition.materials.map((m) => (
                <li key={`${m.name_ar}-${m.unit_ar}`} className="flex justify-between gap-2">
                  <span>{m.name_ar}</span>
                  <bdi className="whitespace-nowrap tabular-nums">
                    {m.quantity.toLocaleString("ar-SA")}
                    {" "}
                    {m.unit_ar}
                  </bdi>
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
              <li key={r.role} className="rounded-sm border border-line bg-white p-3">
                <p className="font-bold">{roleAr[r.role as keyof typeof roleAr] ?? r.role}</p>
                <p className="text-mud">
                  {Object.keys(PERMISSIONS_AR)
                    .filter((p) => r.permissions.includes(p))
                    .map((p) => PERMISSIONS_AR[p])
                    .join("، ")}
                </p>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <li className="flex flex-col gap-1 rounded-sm border border-line bg-white p-3">
      <span className="text-sm text-mud">{label}</span>
      <span className="text-2xl font-bold tabular-nums">{value}</span>
    </li>
  );
}

function WallName({ wall }: { wall: WallCondition }) {
  if (!wall.map_id) return <span className="font-bold">{wall.name_ar}</span>;
  return (
    <Link href={`/dashboard/maps/${wall.map_id}`} className="font-bold hover:text-sadu">
      {wall.name_ar}
    </Link>
  );
}

function StatusPill({ status }: { status: WallCondition["status"] }) {
  return (
    <Badge variant={STATUS_BADGE[status]}>{STATUS_AR[status]}</Badge>
  );
}

function SurveyDue() {
  return (
    <span className="inline-flex items-center gap-1.5 text-xs font-bold text-mud">
      <span aria-hidden="true" className="inline-block size-2 rounded-full bg-moderate" />
      مسح مستحق
    </span>
  );
}

function PendingDraft({ id }: { id: string }) {
  return (
    <MarginNote>
      <Link
        href={`/dashboard/maps/${id}`}
        className="inline-flex min-h-11 items-center text-xs underline underline-offset-4 hover:text-sadu sm:min-h-0"
      >
        مسودة أحدث بانتظار الاعتماد
      </Link>
    </MarginNote>
  );
}

function LoadError({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="pt-6">
      <RetryAlert message={message} onRetry={onRetry} />
    </div>
  );
}

export function ConditionSkeleton() {
  return (
    <div
      role="status"
      aria-label="جارٍ التحميل"
      className="flex animate-pulse flex-col gap-6 pt-6 motion-reduce:animate-none"
    >
      <div className="flex flex-col gap-2">
        <Skeleton className="h-4 w-40 animate-none" />
        <Skeleton className="h-9 w-72 max-w-full animate-none" />
        <Skeleton className="h-4 w-64 max-w-full animate-none" />
      </div>
      <Skeleton className="h-16 animate-none" />
      <div className="grid gap-3 sm:grid-cols-4">
        <Skeleton className="h-20 animate-none sm:col-span-2" />
        <Skeleton className="h-20 animate-none" />
        <Skeleton className="h-20 animate-none" />
      </div>
      <Skeleton className="h-40 animate-none" />
    </div>
  );
}
