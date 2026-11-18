"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { ApiError, type Me, rememberCsrf, request } from "@/lib/api";

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
      router.push("/dashboard");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "تعذر تسجيل الدخول.");
    } finally {
      setPending(false);
    }
  }

  return (
    <form action={submit} className="mx-auto mt-10 flex w-full max-w-sm flex-col gap-3">
      <h1 className="text-2xl font-bold">دخول المفتشين والخبراء</h1>
      <label className="flex flex-col gap-1">
        البريد الإلكتروني
        <input name="email" type="email" required autoComplete="username" dir="ltr" className="rounded-lg border p-2" />
      </label>
      <label className="flex flex-col gap-1">
        كلمة المرور
        <input name="password" type="password" required autoComplete="current-password" dir="ltr" className="rounded-lg border p-2" />
      </label>
      <button disabled={pending} className="rounded-full bg-ink py-2 text-sand">
        {pending ? "…" : "دخول"}
      </button>
      {error && <p role="alert" className="text-urgent">{error}</p>}
    </form>
  );
}
