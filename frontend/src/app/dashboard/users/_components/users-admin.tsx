"use client";

import { Fragment, useCallback, useEffect, useState } from "react";
import { PageSkeleton, RetryAlert } from "@/app/_components/page-status";
import { ApiError, type Site, can, request, roleAr } from "@/lib/api";
import { type ManagedUser, type RoleMatrixRow, listUsers, roleMatrix, seesEverySite } from "@/lib/governance";
import { useMeState } from "@/lib/use-me";
import { NewUserDialog } from "./new-user-dialog";
import { RoleMatrix } from "./role-picker";
import { UserActions } from "./user-actions";

type Directory = { users: ManagedUser[]; matrix: RoleMatrixRow[]; sites: Site[] };

function lastLoginAr(value: string | null): string {
  if (!value) return "لم يدخل بعد";
  return new Date(value).toLocaleString("ar-SA", { dateStyle: "medium", timeStyle: "short" });
}

export function UsersAdmin() {
  const { me, error: meError, retry: retryMe } = useMeState();
  const [directory, setDirectory] = useState<Directory | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState("");
  const [openUser, setOpenUser] = useState<string | null>(null);

  const load = useCallback(
    () =>
      Promise.all([listUsers(), roleMatrix(), request<Site[]>("/sites")]).then(
        ([users, matrix, sites]) => setDirectory({ users, matrix, sites }),
        (e) => setError(e instanceof ApiError ? e.message : "تعذر تحميل الحسابات."),
      ),
    [],
  );

  const allowed = can(me, "administer");

  useEffect(() => {
    if (allowed) load();
  }, [allowed, load]);

  function reload() {
    setError(null);
    load();
  }

  function updated(user: ManagedUser, message: string) {
    setDirectory((current) =>
      current && { ...current, users: current.users.map((u) => (u.id === user.id ? user : u)) },
    );
    setNotice(message);
  }

  if (meError) return <RetryAlert message={meError} onRetry={retryMe} />;
  if (!me) return <PageSkeleton />;
  if (!allowed) {
    return <p className="rounded-xl bg-white/75 p-3">إدارة الحسابات متاحة لمسؤول النظام فقط.</p>;
  }
  if (error && !directory) return <RetryAlert message={error} onRetry={reload} />;
  if (!directory) return <PageSkeleton />;

  const siteName = new Map(directory.sites.map((s) => [s.id, s.name_ar]));

  return (
    <div className="flex flex-col gap-4 pt-2">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-col gap-1">
          <h1 className="text-3xl font-bold leading-snug">الحسابات والصلاحيات</h1>
          <p className="text-sm text-mud">كل تغيير هنا يُسجَّل في سجل التدقيق باسمك.</p>
        </div>
        <NewUserDialog
          matrix={directory.matrix}
          sites={directory.sites}
          onCreated={(user) => {
            setDirectory((current) => current && { ...current, users: [...current.users, user] });
            setNotice(`أُنشئ حساب ${user.email}.`);
          }}
        />
      </header>
      <p role="status" className="text-sm empty:hidden">
        {notice}
      </p>
      <RoleMatrix matrix={directory.matrix} />

      <div className="overflow-x-auto rounded-xl bg-white/75">
        <table className="w-full text-sm">
          <thead className="text-mud">
            <tr className="border-b border-clay/30">
              <th className="p-2 text-start font-normal">الحساب</th>
              <th className="p-2 text-start font-normal">الدور</th>
              <th className="p-2 text-start font-normal">المواقع</th>
              <th className="p-2 text-start font-normal">الحالة</th>
              <th className="p-2 text-start font-normal">آخر دخول</th>
              <th className="p-2 text-start font-normal">
                <span className="sr-only">الإجراءات</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {directory.users.map((user) => {
              const isOpen = openUser === user.id;
              const sites = seesEverySite(user.role) || user.site_ids.length === 0
                ? "كل المواقع"
                : user.site_ids.map((id) => siteName.get(id) ?? id).join("، ");
              return (
                <Fragment key={user.id}>
                  <tr className="border-b border-clay/20 last:border-0">
                  <td className="p-2">
                    <div className="flex flex-col">
                      <span className="font-bold">{user.display_name || "—"}</span>
                      <bdi dir="ltr" className="text-mud">
                        {user.email}
                      </bdi>
                    </div>
                  </td>
                  <td className="p-2">{roleAr[user.role]}</td>
                  <td className="p-2">{sites}</td>
                  <td className="p-2">
                    {user.is_active ? (
                      user.must_change_password ? "بانتظار تغيير كلمة المرور" : "نشط"
                    ) : (
                      <span className="font-bold text-urgent">موقوف</span>
                    )}
                  </td>
                  <td className="p-2">{lastLoginAr(user.last_login_at)}</td>
                  <td className="p-2">
                    <button
                      type="button"
                      aria-expanded={isOpen}
                      aria-controls={isOpen ? `manage-${user.id}` : undefined}
                      onClick={() => setOpenUser(isOpen ? null : user.id)}
                      className="min-h-11 rounded-full border border-ink/30 px-4 hover:bg-ink hover:text-sand"
                    >
                      {isOpen ? "أغلق" : "أدِر"}
                      <span className="sr-only"> حساب {user.email}</span>
                    </button>
                  </td>
                  </tr>
                  {isOpen && (
                    <tr className="border-b border-clay/20 bg-sand/60">
                      <td id={`manage-${user.id}`} colSpan={6} className="p-3">
                        <UserActions
                          user={user}
                          self={user.id === me.id}
                          matrix={directory.matrix}
                          sites={directory.sites}
                          onUpdated={updated}
                        />
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
