"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { ApiError, type Me, rememberCsrf, request } from "@/lib/api";

export type MeState = { me: Me | null; error: string | null; retry: () => void };

const ME_FAILED = "تعذر التحقق من جلستك. تحقق من الاتصال وأعد المحاولة.";

export function useMeState(): MeState {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    request<Me>("/auth/me").then(
      (user) => {
        if (cancelled) return;
        rememberCsrf(user.csrf_token);
        setMe(user);
        setError(null);
      },
      (e) => {
        if (cancelled) return;
        if (e instanceof ApiError && e.status === 401) router.replace("/dashboard/login");
        else setError(ME_FAILED);
      },
    );
    return () => {
      cancelled = true;
    };
  }, [router, attempt]);

  const retry = useCallback(() => {
    setError(null);
    setAttempt((n) => n + 1);
  }, []);

  return { me, error, retry };
}

export function useMe(): Me | null {
  return useMeState().me;
}
