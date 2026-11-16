"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ApiError, type Me, rememberCsrf, request } from "@/lib/api";

/** The signed-in dashboard user; sends anyone else to the login page. */
export function useMe(): Me | null {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);

  useEffect(() => {
    request<Me>("/auth/me").then(
      (user) => {
        rememberCsrf(user.csrf_token);
        setMe(user);
      },
      (e) => {
        if (e instanceof ApiError && e.status === 401) router.replace("/dashboard/login");
      },
    );
  }, [router]);

  return me;
}
