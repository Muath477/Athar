"use client";

import { type FormEvent, type MouseEvent, useId, useState } from "react";
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
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, type Role, type Site, roleAr } from "@/lib/api";
import {
  MIN_PASSWORD_LENGTH,
  type ManagedUser,
  type RoleMatrixRow,
  assignSites,
  changeRole,
  resetPassword,
  seesEverySite,
  setActive,
} from "@/lib/governance";
import { RolePicker } from "./role-picker";
import { SiteChecklist } from "./site-checklist";

type Props = {
  user: ManagedUser;
  self: boolean;
  matrix: RoleMatrixRow[];
  sites: Site[];
  onUpdated: (user: ManagedUser, message: string) => void;
};

export function UserActions({ user, self, matrix, sites, onUpdated }: Props) {
  const [role, setRole] = useState<Role>(user.role);
  const [siteIds, setSiteIds] = useState<string[]>(user.site_ids);
  const [confirmingStatus, setConfirmingStatus] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const passwordId = useId();

  async function run(action: () => Promise<ManagedUser>, message: string) {
    setPending(true);
    setError(null);
    try {
      onUpdated(await action(), message);
      return true;
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "تعذر حفظ التغيير. أعد المحاولة.");
      return false;
    } finally {
      setPending(false);
    }
  }

  async function submitPassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const temporary = String(new FormData(formElement).get("temporary_password"));
    const saved = await run(
      () => resetPassword(user.id, temporary),
      `عُيّنت كلمة مرور مؤقتة لـ ${user.email}، وأُنهيت جلساته المفتوحة.`,
    );
    if (saved) formElement.reset();
  }

  async function toggleActive(event: MouseEvent<HTMLButtonElement>) {
    event.preventDefault();
    const message = user.is_active ? `أُوقف حساب ${user.email} وأُنهيت جلساته.` : `أُعيد تفعيل حساب ${user.email}.`;
    await run(() => setActive(user.id, !user.is_active), message);
    setConfirmingStatus(false);
  }

  return (
    <div className="grid gap-x-8 gap-y-5 lg:grid-cols-2">
      {self && (
        <p className="text-sm text-mud lg:col-span-2">
          لا تستطيع تغيير دورك أو إيقاف حسابك بنفسك. اطلب ذلك من مسؤول آخر.
        </p>
      )}
      <section aria-label="الدور" className="flex flex-col items-start gap-2">
        <RolePicker matrix={matrix} value={role} onChange={setRole} disabled={self || pending} />
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={self || pending || role === user.role}
          onClick={() => run(() => changeRole(user.id, role), `أصبح ${user.email} ${roleAr[role]}.`)}
        >
          احفظ الدور
        </Button>
      </section>

      <section aria-label="المواقع" className="flex flex-col items-start gap-2">
        {seesEverySite(user.role) ? (
          <p className="text-sm text-mud">يرى {roleAr[user.role]} كل المواقع دائمًا.</p>
        ) : (
          <>
            <SiteChecklist sites={sites} selected={siteIds} onChange={setSiteIds} disabled={pending} />
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={pending}
              onClick={() => run(() => assignSites(user.id, siteIds), `حُدّثت مواقع ${user.email}.`)}
            >
              احفظ المواقع
            </Button>
          </>
        )}
      </section>

      <form onSubmit={submitPassword} className="flex flex-col items-start gap-2">
        <div className="flex w-full flex-col gap-1.5">
          <Label htmlFor={passwordId}>كلمة مرور مؤقتة جديدة</Label>
          <Input
            id={passwordId}
            name="temporary_password"
            type="password"
            required
            minLength={MIN_PASSWORD_LENGTH}
            dir="ltr"
            autoComplete="new-password"
            aria-describedby={`${passwordId}-hint`}
          />
          <p id={`${passwordId}-hint`} className="text-xs text-mud">
            سيُطلب من صاحب الحساب تغييرها عند دخوله التالي.
          </p>
        </div>
        <Button variant="outline" size="sm" disabled={pending}>
          عيّن كلمة المرور المؤقتة
        </Button>
      </form>

      <section aria-label="حالة الحساب" className="flex flex-col items-start gap-2">
        <AlertDialog open={confirmingStatus} onOpenChange={setConfirmingStatus}>
          <AlertDialogTrigger asChild>
            <Button
              type="button"
              variant={user.is_active ? "destructive-outline" : "outline"}
              size="sm"
              disabled={self || pending}
            >
              {user.is_active ? "أوقف الحساب…" : "أعد تفعيل الحساب…"}
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>
                {user.is_active ? "أوقف حساب " : "أعد تفعيل حساب "}
                <bdi dir="ltr">{user.email}</bdi>؟
              </AlertDialogTitle>
              <AlertDialogDescription>
                {user.is_active
                  ? "سيُمنع الحساب من الدخول وتُنهى جلساته المفتوحة فورًا."
                  : "سيتمكن الحساب من الدخول مجددًا."}
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogAction
                variant={user.is_active ? "destructive" : "default"}
                disabled={pending}
                onClick={toggleActive}
              >
                {user.is_active ? "أوقف الحساب" : "فعّل الحساب"}
              </AlertDialogAction>
              <AlertDialogCancel>تراجع</AlertDialogCancel>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </section>

      {error && (
        <p role="alert" className="text-urgent lg:col-span-2">
          {error}
        </p>
      )}
    </div>
  );
}
