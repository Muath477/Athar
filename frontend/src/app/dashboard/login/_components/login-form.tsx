"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { ApiError, can, type Me, rememberCsrf, request } from "@/lib/api";

const ERROR_ID = "login-error";
const INPUT_CLASS = "min-h-11 rounded-lg border border-mud/60 bg-white px-3";

function homeFor(me: Me): string {
  if (can(me, "review")) return "/dashboard/maps";
  if (can(me, "manage_site")) return "/dashboard/condition";
  if (can(me, "survey")) return "/dashboard/maps/new";
  return "/dashboard";
}

export function LoginForm() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function submit(form: FormData) {
    setPending(true);
    setError(null);
    try {
      const me = await request<Me>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email: form.get("email"), password: form.get("password") }),
      });
      rememberCsrf(me.csrf_token);
      router.push(homeFor(me));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "تعذر تسجيل الدخول. تحقق من الاتصال وأعد المحاولة.");
    } finally {
      setPending(false);
    }
  }

  const invalid = error !== null;

  return (
    <form action={submit} className="mx-auto mt-10 flex w-full max-w-sm flex-col gap-4">
      <h1 className="text-3xl font-bold leading-snug">دخول المفتشين والخبراء</h1>
      <label className="flex flex-col gap-1">
        البريد الإلكتروني
        <input
          name="email"
          type="email"
          required
          autoComplete="username"
          dir="ltr"
          aria-invalid={invalid || undefined}
          aria-describedby={invalid ? ERROR_ID : undefined}
          className={INPUT_CLASS}
        />
      </label>
      <label className="flex flex-col gap-1">
        كلمة المرور
        <input
          name="password"
          type="password"
          required
          autoComplete="current-password"
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
        {pending ? "جارٍ الدخول…" : "دخول"}
      </button>
      {error && (
        <p id={ERROR_ID} role="alert" className="text-urgent">
          {error}
        </p>
      )}
    </form>
  );
}
