"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";
import { PageSkeleton, RetryAlert } from "@/app/_components/page-status";
import { ApiError, homeFor } from "@/lib/api";
import { MIN_PASSWORD_LENGTH, changeOwnPassword } from "@/lib/governance";
import { useMeState } from "@/lib/use-me";

const ERROR_ID = "password-error";
const INPUT_CLASS = "min-h-11 rounded-lg border border-mud/60 bg-white px-3";

export function PasswordForm() {
  const router = useRouter();
  const { me, error: meError, retry } = useMeState();
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  if (meError) return <RetryAlert message={meError} onRetry={retry} />;
  if (!me) return <PageSkeleton />;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!me) return;
    const form = new FormData(event.currentTarget);
    const next = String(form.get("new_password"));
    if (next !== form.get("confirm_password")) {
      setError("كلمتا المرور الجديدتان غير متطابقتين.");
      return;
    }
    setPending(true);
    setError(null);
    try {
      await changeOwnPassword(String(form.get("current_password")), next);
      router.replace(homeFor({ ...me, must_change_password: false }));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "تعذر تغيير كلمة المرور. أعد المحاولة.");
      setPending(false);
    }
  }

  const invalid = error !== null;
  const describedBy = invalid ? `${ERROR_ID} password-hint` : "password-hint";

  return (
    <form onSubmit={submit} className="mx-auto mt-10 flex w-full max-w-sm flex-col gap-4">
      <h1 className="text-3xl font-bold leading-snug">عيّن كلمة مرور جديدة</h1>
      {me.must_change_password && (
        <p className="rounded-xl bg-white/75 p-3 text-sm leading-relaxed">
          أنشأ مسؤول النظام كلمة مرور مؤقتة لحسابك. اختر كلمة مرور خاصة بك قبل المتابعة.
        </p>
      )}
      <label className="flex flex-col gap-1">
        كلمة المرور الحالية
        <input
          name="current_password"
          type="password"
          required
          autoComplete="current-password"
          dir="ltr"
          aria-invalid={invalid || undefined}
          aria-describedby={invalid ? ERROR_ID : undefined}
          className={INPUT_CLASS}
        />
      </label>
      <label className="flex flex-col gap-1">
        كلمة المرور الجديدة
        <input
          name="new_password"
          type="password"
          required
          minLength={MIN_PASSWORD_LENGTH}
          autoComplete="new-password"
          dir="ltr"
          aria-invalid={invalid || undefined}
          aria-describedby={describedBy}
          className={INPUT_CLASS}
        />
        <span id="password-hint" className="text-sm text-mud">
          {MIN_PASSWORD_LENGTH.toLocaleString("ar-SA")} حرفًا على الأقل، وعبارة طويلة أسهل في التذكر.
        </span>
      </label>
      <label className="flex flex-col gap-1">
        أعد كتابة كلمة المرور الجديدة
        <input
          name="confirm_password"
          type="password"
          required
          minLength={MIN_PASSWORD_LENGTH}
          autoComplete="new-password"
          dir="ltr"
          aria-invalid={invalid || undefined}
          aria-describedby={invalid ? ERROR_ID : undefined}
          className={INPUT_CLASS}
        />
      </label>
      <button
        disabled={pending}
        className="min-h-11 rounded-full bg-sadu px-6 font-bold text-sand hover:bg-ink disabled:opacity-50"
      >
        {pending ? "نحفظ كلمة المرور…" : "احفظ كلمة المرور"}
      </button>
      {error && (
        <p id={ERROR_ID} role="alert" className="text-urgent">
          {error}
        </p>
      )}
    </form>
  );
}
