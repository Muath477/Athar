"use client";

import { type FormEvent, useCallback, useEffect, useState } from "react";
import { PageSkeleton, RetryAlert } from "@/app/_components/page-status";
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

const FIELD_CLASS = "min-h-11 rounded-lg border border-mud/60 bg-white px-3";
const SECONDARY = "min-h-11 rounded-full border border-ink/30 px-5 hover:bg-ink hover:text-sand disabled:opacity-50";

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
    return <p className="rounded-xl bg-white/75 p-3">سجل التدقيق متاح لمسؤول النظام وممثل هيئة التراث.</p>;
  }

  const pages = result ? Math.max(1, Math.ceil(result.total / result.page_size)) : 1;

  return (
    <div className="flex flex-col gap-4 pt-2">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-col gap-1">
          <h1 className="text-3xl font-bold leading-snug">سجل التدقيق</h1>
          <p className="text-sm text-mud">من فعل ماذا ومتى: الدخول، المخططات واعتمادها، الحسابات، وحذف الصور.</p>
        </div>
        {can(me, "export") && (
          <a href={auditCsvUrl(filters)} download className={`${SECONDARY} inline-flex items-center`}>
            نزّل السجل CSV
          </a>
        )}
      </header>

      <form onSubmit={applyFilters} className="flex flex-wrap items-end gap-3 rounded-xl bg-white/60 p-3 text-sm">
        <label className="flex flex-col gap-1">
          المنفّذ (البريد)
          <input name="actor" type="search" dir="ltr" defaultValue={filters.actor} className={FIELD_CLASS} />
        </label>
        <label className="flex flex-col gap-1">
          نوع الإجراء
          <select name="action" defaultValue={filters.action} className={FIELD_CLASS}>
            <option value="">كل الإجراءات</option>
            {ACTION_GROUPS.map((group) => (
              <option key={group.prefix} value={group.prefix}>
                {group.label}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          الهدف
          <select name="target_type" defaultValue={filters.target_type} className={FIELD_CLASS}>
            <option value="">كل الأهداف</option>
            {TARGET_TYPES.map((target) => (
              <option key={target.value} value={target.value}>
                {target.label}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          من يوم
          <input name="from" type="date" defaultValue={filters.from} className={FIELD_CLASS} />
        </label>
        <label className="flex flex-col gap-1">
          إلى يوم
          <input name="to" type="date" defaultValue={filters.to} className={FIELD_CLASS} />
        </label>
        <button className="min-h-11 rounded-full bg-sadu px-6 font-bold text-sand hover:bg-ink">طبّق التصفية</button>
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
            <p className="rounded-xl bg-white/75 p-3">لا سجلات تطابق التصفية.</p>
          ) : (
            <div className="overflow-x-auto rounded-xl bg-white/75">
              <table className="w-full text-sm">
                <thead className="text-mud">
                  <tr className="border-b border-clay/30">
                    <th className="p-2 text-start font-normal">الوقت</th>
                    <th className="p-2 text-start font-normal">المنفّذ</th>
                    <th className="p-2 text-start font-normal">الإجراء</th>
                    <th className="p-2 text-start font-normal">الهدف</th>
                  </tr>
                </thead>
                <tbody>
                  {result.entries.map((entry) => (
                    <tr key={entry.id} className="border-b border-clay/20 last:border-0">
                      <td className="whitespace-nowrap p-2">{momentAr(entry.at)}</td>
                      <td className="p-2">
                        {entry.actor_email ? <bdi dir="ltr">{entry.actor_email}</bdi> : "النظام"}
                      </td>
                      <td className="p-2">{auditActionAr(entry.action)}</td>
                      <td className="p-2">
                        {targetAr(entry)}{" "}
                        <bdi dir="ltr" className="text-mud">
                          {entry.target_id.slice(0, 8)}
                        </bdi>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <nav aria-label="صفحات السجل" className="flex flex-wrap gap-3">
            <button type="button" disabled={page <= 1} onClick={() => setPage(page - 1)} className={SECONDARY}>
              الصفحة السابقة
            </button>
            <button type="button" disabled={page >= pages} onClick={() => setPage(page + 1)} className={SECONDARY}>
              الصفحة التالية
            </button>
          </nav>
        </>
      )}
    </div>
  );
}
