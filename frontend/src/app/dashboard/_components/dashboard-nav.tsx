"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const SECTIONS = [
  { href: "/dashboard", label: "الموقع ثلاثي الأبعاد", exact: true },
  { href: "/dashboard/condition", label: "حالة الموقع", exact: false },
  { href: "/dashboard/watch", label: "الرصد من الفضاء", exact: false },
  { href: "/dashboard/maps", label: "مخططات تلف الجدران", exact: false },
  { href: "/dashboard/review", label: "قائمة المراجعة", exact: false },
];

export function DashboardNav() {
  const pathname = usePathname();
  if (pathname.startsWith("/dashboard/login")) return null;

  return (
    <nav aria-label="أقسام لوحة المتابعة" className="no-print -mx-4 overflow-x-auto border-b border-clay/40 px-4">
      <ul className="flex min-w-max gap-1">
        {SECTIONS.map((section) => {
          const active = section.exact ? pathname === section.href : pathname.startsWith(section.href);
          return (
            <li key={section.href}>
              <Link
                href={section.href}
                aria-current={active ? "page" : undefined}
                className={`-mb-px inline-block border-b-[3px] px-3 py-2.5 text-sm transition-colors ${
                  active ? "border-sadu font-bold text-sadu" : "border-transparent text-mud hover:border-clay hover:text-ink"
                }`}
              >
                {section.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
