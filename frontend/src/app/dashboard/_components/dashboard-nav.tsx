"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { type Permission, can, rememberCsrf, request, roleAr } from "@/lib/api";
import { useMe } from "@/lib/use-me";
import { cn } from "@/lib/utils";

type Section = { href: string; label: string; short: string | null; exact: boolean; permission?: Permission };

const SECTIONS: Section[] = [
  { href: "/dashboard", label: "الموقع ثلاثي الأبعاد", short: null, exact: true },
  { href: "/dashboard/condition", label: "حالة الموقع", short: null, exact: false },
  { href: "/dashboard/watch", label: "الرصد من الفضاء", short: null, exact: false },
  { href: "/dashboard/maps", label: "مخططات تلف الجدران", short: "المخططات", exact: false },
  { href: "/dashboard/uploads", label: "رفع الصور", short: null, exact: false, permission: "survey" },
  { href: "/dashboard/devices", label: "الكاميرات والأجهزة", short: "الأجهزة", exact: false, permission: "read" },
  { href: "/dashboard/review", label: "قائمة المراجعة", short: "المراجعة", exact: false },
];

export function DashboardNav() {
  const pathname = usePathname();
  const me = useMe();
  const current = useRef<HTMLAnchorElement>(null);
  const sections = SECTIONS.filter((section) => !section.permission || can(me, section.permission));

  useEffect(() => {
    current.current?.scrollIntoView({ inline: "nearest", block: "nearest" });
  }, [pathname]);

  if (pathname.startsWith("/dashboard/login")) return null;

  return (
    <div className="no-print flex flex-col">
      <SignedInUser />
      <nav aria-label="أقسام لوحة المتابعة" className="-mx-4 scroll-px-4 overflow-x-auto border-b border-line px-4">
        <ul className="flex min-w-max gap-1">
          {sections.map((section) => {
            const active = section.exact ? pathname === section.href : pathname.startsWith(section.href);
            return (
              <li key={section.href}>
                <Link
                  ref={active ? current : undefined}
                  href={section.href}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "-mb-px inline-flex min-h-11 items-center border-b-2 px-3 text-sm transition-colors duration-150",
                    active ? "border-sadu font-bold text-sadu" : "border-transparent text-mud hover:border-clay hover:text-ink",
                  )}
                >
                  {section.short ? (
                    <>
                      <span className="sm:hidden">{section.short}</span>
                      <span className="hidden sm:inline">{section.label}</span>
                    </>
                  ) : (
                    section.label
                  )}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </div>
  );
}

function SignedInUser() {
  const me = useMe();
  const router = useRouter();
  const [leaving, setLeaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function signOut() {
    setLeaving(true);
    setError(null);
    try {
      await request("/auth/logout", { method: "POST" });
      rememberCsrf(null);
      router.replace("/dashboard/login");
    } catch {
      setError("تعذر تسجيل الخروج. أعد المحاولة.");
      setLeaving(false);
    }
  }

  if (!me) return null;

  return (
    <div className="flex flex-wrap items-center justify-end gap-x-3 gap-y-1 text-sm">
      <Avatar className="size-8" aria-hidden="true">
        <AvatarFallback className="font-latin uppercase">{me.email.charAt(0)}</AvatarFallback>
      </Avatar>
      <p className="min-w-0 text-mud">
        <bdi className="inline-block max-w-56 truncate align-bottom text-ink">{me.email}</bdi> · {roleAr[me.role]}
      </p>
      <Button type="button" variant="ghost" size="sm" onClick={signOut} disabled={leaving}>
        {leaving ? "نسجّل خروجك…" : "تسجيل الخروج"}
      </Button>
      {error && (
        <p role="alert" className="basis-full text-end text-urgent">
          {error}
        </p>
      )}
    </div>
  );
}
