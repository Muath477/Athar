"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Suspense } from "react";
import { cn } from "@/lib/utils";

const LINKS = [
  { href: "/passport", label: "جوازي" },
  { href: "/dashboard", label: "لوحة المتابعة" },
];

export function SiteNav() {
  return (
    <Suspense fallback={<NavLinks pathname="" />}>
      <CurrentNavLinks />
    </Suspense>
  );
}

function CurrentNavLinks() {
  return <NavLinks pathname={usePathname()} />;
}

function NavLinks({ pathname }: { pathname: string }) {
  return (
    <nav aria-label="الرئيسية" className="flex gap-1 text-sm">
      {LINKS.map((link) => {
        const active = pathname === link.href || pathname.startsWith(`${link.href}/`);
        return (
          <Link
            key={link.href}
            href={link.href}
            aria-current={active ? "page" : undefined}
            className={cn(
              "inline-flex min-h-11 items-center border-b-2 px-2 transition-colors duration-150",
              active ? "border-sadu font-bold text-sadu" : "border-transparent text-mud hover:border-clay hover:text-ink",
            )}
          >
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}
