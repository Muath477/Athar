"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";
import { PageSkeleton, RetryAlert } from "@/app/_components/page-status";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, homeFor } from "@/lib/api";
import { MIN_PASSWORD_LENGTH, changeOwnPassword } from "@/lib/governance";
import { useMeState } from "@/lib/use-me";

const ERROR_ID = "password-error";

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
    <form onSubmit={submit} className="mx-auto mt-10 flex w-full max-w-sm flex-col gap-5">
      <h1 className="text-3xl font-bold">عيّن كلمة مرور جديدة</h1>
      {me.must_change_password && (
        <p className="rounded-sm border border-line bg-white p-3 text-sm leading-relaxed">
          أنشأ مسؤول النظام كلمة مرور مؤقتة لحسابك. اختر كلمة مرور خاصة بك قبل المتابعة.
        </p>
      )}
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="current-password">كلمة المرور الحالية</Label>
        <Input
          id="current-password"
          name="current_password"
          type="password"
          required
          autoComplete="current-password"
          dir="ltr"
          aria-invalid={invalid || undefined}
          aria-describedby={invalid ? ERROR_ID : undefined}
        />
      </div>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="new-password">كلمة المرور الجديدة</Label>
        <Input
          id="new-password"
          name="new_password"
          type="password"
          required
          minLength={MIN_PASSWORD_LENGTH}
          autoComplete="new-password"
          dir="ltr"
          aria-invalid={invalid || undefined}
          aria-describedby={describedBy}
        />
        <p id="password-hint" className="text-xs text-mud">
          {MIN_PASSWORD_LENGTH.toLocaleString("ar-SA")} حرفًا على الأقل، وعبارة طويلة أسهل في التذكر.
        </p>
      </div>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="confirm-password">أعد كتابة كلمة المرور الجديدة</Label>
        <Input
          id="confirm-password"
          name="confirm_password"
          type="password"
          required
          minLength={MIN_PASSWORD_LENGTH}
          autoComplete="new-password"
          dir="ltr"
          aria-invalid={invalid || undefined}
          aria-describedby={invalid ? ERROR_ID : undefined}
        />
      </div>
      <Button size="lg" disabled={pending}>
        {pending ? "نحفظ كلمة المرور…" : "احفظ كلمة المرور"}
      </Button>
      {error && (
        <p id={ERROR_ID} role="alert" className="text-urgent">
          {error}
        </p>
      )}
    </form>
  );
}
