"use client";

import { type FormEvent, useRef, useState } from "react";
import { ApiError, type Role, type Site } from "@/lib/api";
import {
  MIN_PASSWORD_LENGTH,
  type ManagedUser,
  type RoleMatrixRow,
  createUser,
  seesEverySite,
} from "@/lib/governance";
import { FIELD_CLASS, RolePicker } from "./role-picker";
import { SiteChecklist } from "./site-checklist";

const ERROR_ID = "new-user-error";

export function NewUserDialog({
  matrix,
  sites,
  onCreated,
}: {
  matrix: RoleMatrixRow[];
  sites: Site[];
  onCreated: (user: ManagedUser) => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const opener = useRef<HTMLButtonElement>(null);
  const [role, setRole] = useState<Role>("inspector");
  const [siteIds, setSiteIds] = useState<string[]>([]);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function open() {
    setError(null);
    dialog.current?.showModal();
  }

  function close() {
    dialog.current?.close();
    opener.current?.focus();
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    setPending(true);
    setError(null);
    try {
      const created = await createUser({
        email: String(form.get("email")),
        display_name: String(form.get("display_name")),
        role,
        password: String(form.get("password")),
        site_ids: seesEverySite(role) ? [] : siteIds,
      });
      formElement.reset();
      setRole("inspector");
      setSiteIds([]);
      close();
      onCreated(created);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "تعذر إنشاء الحساب. أعد المحاولة.");
    } finally {
      setPending(false);
    }
  }

  const invalid = error !== null;

  return (
    <>
      <button
        ref={opener}
        type="button"
        onClick={open}
        className="min-h-11 rounded-full bg-sadu px-6 font-bold text-sand hover:bg-ink"
      >
        أضف حسابًا
      </button>
      <dialog
        ref={dialog}
        aria-labelledby="new-user-title"
        className="m-auto w-full max-w-lg rounded-xl bg-sand p-0 text-ink backdrop:bg-ink/50"
      >
        <form onSubmit={submit} className="flex flex-col gap-4 p-5">
          <h2 id="new-user-title" className="text-xl font-bold">
            حساب جديد
          </h2>
          <label className="flex flex-col gap-1">
            البريد الإلكتروني
            <input
              name="email"
              type="email"
              required
              dir="ltr"
              autoComplete="off"
              aria-invalid={invalid || undefined}
              aria-describedby={invalid ? ERROR_ID : undefined}
              className={FIELD_CLASS}
            />
          </label>
          <label className="flex flex-col gap-1">
            الاسم الظاهر
            <input name="display_name" maxLength={120} autoComplete="off" className={FIELD_CLASS} />
          </label>
          <RolePicker matrix={matrix} value={role} onChange={setRole} />
          <label className="flex flex-col gap-1">
            كلمة مرور مؤقتة
            <input
              name="password"
              type="password"
              required
              minLength={MIN_PASSWORD_LENGTH}
              dir="ltr"
              autoComplete="new-password"
              aria-describedby="new-user-password-hint"
              className={FIELD_CLASS}
            />
            <span id="new-user-password-hint" className="text-sm text-mud">
              {MIN_PASSWORD_LENGTH.toLocaleString("ar-SA")} حرفًا على الأقل. سلّمها لصاحب الحساب، وسيُطلب منه تغييرها
              عند أول دخول.
            </span>
          </label>
          {!seesEverySite(role) && (
            <SiteChecklist sites={sites} selected={siteIds} onChange={setSiteIds} />
          )}
          {error && (
            <p id={ERROR_ID} role="alert" className="text-urgent">
              {error}
            </p>
          )}
          <div className="flex flex-wrap gap-3">
            <button
              disabled={pending}
              className="min-h-11 rounded-full bg-sadu px-6 font-bold text-sand hover:bg-ink disabled:opacity-50"
            >
              {pending ? "ننشئ الحساب…" : "أنشئ الحساب"}
            </button>
            <button
              type="button"
              onClick={close}
              className="min-h-11 rounded-full border border-ink/30 px-5 hover:bg-ink hover:text-sand"
            >
              ألغِ
            </button>
          </div>
        </form>
      </dialog>
    </>
  );
}
