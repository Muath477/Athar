"use client";

import { type FormEvent, useCallback, useEffect, useState } from "react";
import { PageSkeleton, RetryAlert } from "@/app/_components/page-status";
import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ApiError, can } from "@/lib/api";
import {
  ACTION_GROUPS,
  type AuditEntry,
  type AuditFilters,
  type AuditPage,
  EMPTY_FILTERS,
  TARGET_TYPES,
  auditActionAr,
  auditCsvUrl,
  auditEntries,
  listAudit,
} from "@/lib/governance";
import { countAr } from "@/lib/plural";
import { useMeState } from "@/lib/use-me";

function momentAr(value: string): string {
  return new Date(value).toLocaleString("ar-SA", { dateStyle: "medium", timeStyle: "short" });
}

function targetAr(entry: AuditEntry): string {
  return TARGET_TYPES.find((t) => t.value === entry.target_type)?.label ?? entry.target_type;
}

export function AuditLog() {
  const { me, error: meError, retry: retryMe } = useMeState();
  const [filters, setFilters] = useState<AuditFilters>(EMPTY_FILTERS);
  const [page, setPage] = useState(1);
  const [result, setResult] = useState<AuditPage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const allowed = can(me, "read_audit");

  const load = useCallback(
    () =>
      listAudit(filters, page).then(setResult, (e) =>
        setError(e instanceof ApiError ? e.message : "تعذر تحميل سجل التدقيق."),
      ),
    [filters, page],
  );

  useEffect(() => {
    if (allowed) load();
  }, [allowed, load]);

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setError(null);
    setPage(1);
    setFilters({
      actor: String(form.get("actor") ?? ""),
      action: String(form.get("action") ?? ""),
      target_type: String(form.get("target_type") ?? ""),
      from: String(form.get("from") ?? ""),
      to: String(form.get("to") ?? ""),
    });
  }

  function retry() {
    setError(null);
    load();
  }

  if (meError) return <RetryAlert message={meError} onRetry={retryMe} />;
  if (!me) return <PageSkeleton />;
  if (!allowed) {
    return (
      <p className="mt-6 rounded-sm border border-line bg-white p-3">
        سجل التدقيق متاح لمسؤول النظام وممثل هيئة التراث.
      </p>
    );
  }

  const pages = result ? Math.max(1, Math.ceil(result.total / result.page_size)) : 1;

  return (
    <div className="flex flex-col gap-5 pt-2">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-col gap-1">
          <h1 className="text-3xl font-bold leading-snug">سجل التدقيق</h1>
          <p className="text-sm text-mud">من فعل ماذا ومتى: الدخول، المخططات واعتمادها، الحسابات، وحذف الصور.</p>
        </div>
        {can(me, "export") && (
          <a href={auditCsvUrl(filters)} download className={buttonVariants({ variant: "outline" })}>
            نزّل السجل CSV
          </a>
        )}
      </header>

      <form
        onSubmit={applyFilters}
        aria-label="تصفية السجل"
        className="grid gap-3 border-y border-line py-4 sm:grid-cols-2 lg:grid-cols-[repeat(5,minmax(0,1fr))_auto] lg:items-end"
      >
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="audit-actor">المنفّذ (البريد)</Label>
          <Input id="audit-actor" name="actor" type="search" dir="ltr" defaultValue={filters.actor} />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="audit-action">نوع الإجراء</Label>
          <NativeSelect id="audit-action" name="action" defaultValue={filters.action}>
            <option value="">كل الإجراءات</option>
            {ACTION_GROUPS.map((group) => (
              <option key={group.prefix} value={group.prefix}>
                {group.label}
              </option>
            ))}
          </NativeSelect>
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="audit-target">الهدف</Label>
          <NativeSelect id="audit-target" name="target_type" defaultValue={filters.target_type}>
            <option value="">كل الأهداف</option>
            {TARGET_TYPES.map((target) => (
              <option key={target.value} value={target.value}>
                {target.label}
              </option>
            ))}
          </NativeSelect>
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="audit-from">من يوم</Label>
          <Input id="audit-from" name="from" type="date" defaultValue={filters.from} />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="audit-to">إلى يوم</Label>
          <Input id="audit-to" name="to" type="date" defaultValue={filters.to} />
        </div>
        <Button className="sm:col-span-2 lg:col-span-1">طبّق التصفية</Button>
      </form>

      {error && <RetryAlert message={error} onRetry={retry} />}
      {!result ? (
        <PageSkeleton />
      ) : (
        <>
          <p role="status" className="text-sm text-mud">
            {countAr(result.total, auditEntries)} · الصفحة {page.toLocaleString("ar-SA")} من{" "}
            {pages.toLocaleString("ar-SA")}
          </p>
          {result.entries.length === 0 ? (
            <p className="rounded-sm border border-line bg-white p-3">
              لا سجلات تطابق التصفية. وسّع المدة أو أزل أحد الشروط.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>الوقت</TableHead>
                  <TableHead>المنفّذ</TableHead>
                  <TableHead>الإجراء</TableHead>
                  <TableHead>الهدف</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {result.entries.map((entry) => (
                  <TableRow key={entry.id}>
                    <TableCell className="whitespace-nowrap">{momentAr(entry.at)}</TableCell>
                    <TableCell>{entry.actor_email ? <bdi dir="ltr">{entry.actor_email}</bdi> : "النظام"}</TableCell>
                    <TableCell>{auditActionAr(entry.action)}</TableCell>
                    <TableCell>
                      {targetAr(entry)}{" "}
                      <bdi dir="ltr" className="font-latin text-mud">
                        {entry.target_id.slice(0, 8)}
                      </bdi>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
          <nav aria-label="صفحات السجل" className="flex flex-wrap gap-2">
            <Button type="button" variant="outline" disabled={page <= 1} onClick={() => setPage(page - 1)}>
              الصفحة السابقة
            </Button>
            <Button type="button" variant="outline" disabled={page >= pages} onClick={() => setPage(page + 1)}>
              الصفحة التالية
            </Button>
          </nav>
        </>
      )}
    </div>
  );
}
