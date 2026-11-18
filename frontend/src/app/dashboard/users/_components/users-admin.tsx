"use client";

import { Fragment, useCallback, useEffect, useState } from "react";
import { PageSkeleton, RetryAlert } from "@/app/_components/page-status";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ApiError, type Site, can, request, roleAr } from "@/lib/api";
import { type ManagedUser, type RoleMatrixRow, listUsers, roleMatrix, seesEverySite } from "@/lib/governance";
import { useMeState } from "@/lib/use-me";
import { NewUserDialog } from "./new-user-dialog";
import { RoleMatrix } from "./role-picker";
import { UserActions } from "./user-actions";

type Directory = { users: ManagedUser[]; matrix: RoleMatrixRow[]; sites: Site[] };

function StatusBadge({ user }: { user: ManagedUser }) {
  if (!user.is_active) return <Badge variant="ink">موقوف</Badge>;
  if (user.must_change_password) return <Badge variant="outline">بانتظار تغيير كلمة المرور</Badge>;
  return <Badge variant="muted">نشط</Badge>;
}

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
    setDirectory(
      (current) => current && { ...current, users: current.users.map((u) => (u.id === user.id ? user : u)) },
    );
    setNotice(message);
  }

  if (meError) return <RetryAlert message={meError} onRetry={retryMe} />;
  if (!me) return <PageSkeleton />;
  if (!allowed) {
    return <p className="mt-6 rounded-sm border border-line bg-white p-3">إدارة الحسابات متاحة لمسؤول النظام فقط.</p>;
  }
  if (error && !directory) return <RetryAlert message={error} onRetry={reload} />;
  if (!directory) return <PageSkeleton />;

  const siteName = new Map(directory.sites.map((s) => [s.id, s.name_ar]));

  return (
    <div className="flex flex-col gap-5 pt-2">
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

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>الحساب</TableHead>
            <TableHead>الدور</TableHead>
            <TableHead>المواقع</TableHead>
            <TableHead>الحالة</TableHead>
            <TableHead>آخر دخول</TableHead>
            <TableHead>
              <span className="sr-only">الإجراءات</span>
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {directory.users.map((user) => {
            const isOpen = openUser === user.id;
            const sites =
              seesEverySite(user.role) || user.site_ids.length === 0
                ? "كل المواقع"
                : user.site_ids.map((id) => siteName.get(id) ?? id).join("، ");
            return (
              <Fragment key={user.id}>
                <TableRow className={isOpen ? "border-line bg-sand" : undefined}>
                  <TableCell>
                    <div className="flex flex-col">
                      <span className="font-bold">{user.display_name || "—"}</span>
                      <bdi dir="ltr" className="text-mud">
                        {user.email}
                      </bdi>
                    </div>
                  </TableCell>
                  <TableCell>{roleAr[user.role]}</TableCell>
                  <TableCell>{sites}</TableCell>
                  <TableCell>
                    <StatusBadge user={user} />
                  </TableCell>
                  <TableCell className="whitespace-nowrap">{lastLoginAr(user.last_login_at)}</TableCell>
                  <TableCell className="text-end">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      aria-expanded={isOpen}
                      aria-controls={isOpen ? `manage-${user.id}` : undefined}
                      onClick={() => setOpenUser(isOpen ? null : user.id)}
                    >
                      {isOpen ? "أغلق" : "أدِر"}
                      <span className="sr-only"> حساب {user.email}</span>
                    </Button>
                  </TableCell>
                </TableRow>
                {isOpen && (
                  <TableRow className="bg-sand">
                    <TableCell id={`manage-${user.id}`} colSpan={6} className="p-4">
                      <UserActions
                        user={user}
                        self={user.id === me.id}
                        matrix={directory.matrix}
                        sites={directory.sites}
                        onUpdated={updated}
                      />
                    </TableCell>
                  </TableRow>
                )}
              </Fragment>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
