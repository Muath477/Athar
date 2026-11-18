"use client";

import { type FormEvent, useRef, useState } from "react";
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
import { FIELD_CLASS, RolePicker } from "./role-picker";
import { SiteChecklist } from "./site-checklist";

const SECONDARY = "min-h-11 rounded-full border border-ink/30 px-5 hover:bg-ink hover:text-sand disabled:opacity-50";

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
  const statusButton = useRef<HTMLButtonElement>(null);

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

  async function toggleActive() {
    const message = user.is_active
      ? `أُوقف حساب ${user.email} وأُنهيت جلساته.`
      : `أُعيد تفعيل حساب ${user.email}.`;
    await run(() => setActive(user.id, !user.is_active), message);
    closeConfirm();
  }

  function closeConfirm() {
    setConfirmingStatus(false);
    requestAnimationFrame(() => statusButton.current?.focus());
  }

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {self && (
        <p className="text-sm text-mud lg:col-span-2">
          لا تستطيع تغيير دورك أو إيقاف حسابك بنفسك. اطلب ذلك من مسؤول آخر.
        </p>
      )}
      <section aria-label="الدور" className="flex flex-col items-start gap-2">
        <RolePicker matrix={matrix} value={role} onChange={setRole} disabled={self || pending} />
        <button
          type="button"
          disabled={self || pending || role === user.role}
          onClick={() => run(() => changeRole(user.id, role), `أصبح ${user.email} ${roleAr[role]}.`)}
          className={SECONDARY}
        >
          احفظ الدور
        </button>
      </section>

      <section aria-label="المواقع" className="flex flex-col items-start gap-2">
        {seesEverySite(user.role) ? (
          <p className="text-sm text-mud">يرى {roleAr[user.role]} كل المواقع دائمًا.</p>
        ) : (
          <>
            <SiteChecklist sites={sites} selected={siteIds} onChange={setSiteIds} disabled={pending} />
            <button
              type="button"
              disabled={pending}
              onClick={() => run(() => assignSites(user.id, siteIds), `حُدّثت مواقع ${user.email}.`)}
              className={SECONDARY}
            >
              احفظ المواقع
            </button>
          </>
        )}
      </section>

      <form onSubmit={submitPassword} className="flex flex-col items-start gap-2">
        <label className="flex flex-col gap-1">
          كلمة مرور مؤقتة جديدة
          <input
            name="temporary_password"
            type="password"
            required
            minLength={MIN_PASSWORD_LENGTH}
            dir="ltr"
            autoComplete="new-password"
            className={FIELD_CLASS}
          />
        </label>
        <p className="text-sm text-mud">سيُطلب من صاحب الحساب تغييرها عند دخوله التالي.</p>
        <button disabled={pending} className={SECONDARY}>
          عيّن كلمة المرور المؤقتة
        </button>
      </form>

      <section aria-label="حالة الحساب" className="flex flex-col items-start gap-2">
        <button
          ref={statusButton}
          type="button"
          disabled={self || pending || confirmingStatus}
          aria-expanded={confirmingStatus}
          onClick={() => setConfirmingStatus(true)}
          className={SECONDARY}
        >
          {user.is_active ? "أوقف الحساب…" : "أعد تفعيل الحساب…"}
        </button>
        {confirmingStatus && (
          <div role="group" aria-label="تأكيد تغيير الحالة" className="flex flex-wrap items-center gap-3">
            <span>
              {user.is_active
                ? "سيُمنع الحساب من الدخول وتُنهى جلساته المفتوحة فورًا. أتابع؟"
                : "سيتمكن الحساب من الدخول مجددًا. أتابع؟"}
            </span>
            <button
              type="button"
              autoFocus
              disabled={pending}
              onClick={toggleActive}
              className="min-h-11 rounded-full bg-urgent px-5 font-bold text-sand disabled:opacity-50"
            >
              {user.is_active ? "أوقف الحساب" : "فعّل الحساب"}
            </button>
            <button type="button" onClick={closeConfirm} className={SECONDARY}>
              تراجع
            </button>
          </div>
        )}
      </section>

      {error && (
        <p role="alert" className="text-urgent lg:col-span-2">
          {error}
        </p>
      )}
    </div>
  );
}
