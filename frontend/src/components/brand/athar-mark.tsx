import { cn } from "@/lib/utils";

export function AtharMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 64 64" aria-hidden="true" focusable="false" className={cn("size-8 shrink-0", className)}>
      <rect x="16" y="6" width="36" height="52" fill="none" className="stroke-ink" strokeWidth="2.5" />
      <path d="M22 18 H46 M22 26 H46 M22 34 H46" fill="none" className="stroke-ink" strokeWidth="2" />
      <path d="M10 14 C4 22 4 36 10 46" fill="none" className="stroke-sadu" strokeWidth="3" strokeLinecap="round" />
      <circle cx="34" cy="46" r="4" className="fill-watch" />
    </svg>
  );
}

export function AtharWordmark({ className }: { className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-2", className)}>
      <AtharMark />
      <span className="text-2xl leading-none font-bold">أثر</span>
    </span>
  );
}
