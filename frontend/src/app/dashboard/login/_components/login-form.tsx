"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { AtharMark } from "@/components/brand/athar-mark";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, homeFor, type Me, rememberCsrf, request } from "@/lib/api";

const ERROR_ID = "login-error";

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
    <form action={submit} className="mx-auto mt-10 flex w-full max-w-sm flex-col gap-5">
      <div className="flex flex-col gap-3">
        <AtharMark className="size-12" />
        <h1 className="text-3xl font-bold">دخول المفتشين والخبراء</h1>
      </div>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="login-email">البريد الإلكتروني</Label>
        <Input
          id="login-email"
          name="email"
          type="email"
          required
          autoComplete="username"
          dir="ltr"
          aria-invalid={invalid || undefined}
          aria-describedby={invalid ? ERROR_ID : undefined}
        />
      </div>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="login-password">كلمة المرور</Label>
        <Input
          id="login-password"
          name="password"
          type="password"
          required
          autoComplete="current-password"
          dir="ltr"
          aria-invalid={invalid || undefined}
          aria-describedby={invalid ? ERROR_ID : undefined}
        />
      </div>
      <Button disabled={pending} size="lg">
        {pending ? "جارٍ الدخول…" : "دخول"}
      </Button>
      {error && (
        <p id={ERROR_ID} role="alert" className="text-urgent">
          {error}
        </p>
      )}
    </form>
  );
}
