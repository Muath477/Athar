import Link from "next/link";
import type { ConversationSummary } from "@/lib/assistant";
import { buttonVariants } from "@/components/ui/button";

function updatedAr(value: string): string {
  return new Date(value).toLocaleString("ar-SA", { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" });
}

export function ConversationList({
  conversations,
  activeId,
  onStartNew,
  disabled,
}: {
  conversations: ConversationSummary[] | null;
  activeId: string | null;
  onStartNew: () => void;
  disabled: boolean;
}) {
  return (
    <nav aria-label="محادثاتي" className="flex flex-col gap-2">
      <button
        type="button"
        onClick={onStartNew}
        disabled={disabled}
        className={buttonVariants()}
      >
        ابدأ محادثة جديدة
      </button>
      {conversations === null ? (
        <div role="status" aria-label="جارٍ تحميل المحادثات" className="flex animate-pulse flex-col gap-2 motion-reduce:animate-none">
          <div className="h-11 rounded-sm bg-clay/60" />
          <div className="h-11 rounded-sm bg-clay/60" />
        </div>
      ) : conversations.length === 0 ? (
        <p className="rounded-sm bg-white/60 p-3 text-sm text-mud">لا محادثات بعد. اكتب سؤالك أو أرفق صورة لتبدأ.</p>
      ) : (
        <ul className="flex flex-col gap-1">
          {conversations.map((c) => {
            const active = c.id === activeId;
            return (
              <li key={c.id}>
                <Link
                  href={`/dashboard/assistant?c=${c.id}`}
                  aria-current={active ? "page" : undefined}
                  aria-disabled={disabled || undefined}
                  tabIndex={disabled ? -1 : undefined}
                  className={`flex min-h-11 flex-col justify-center rounded-sm px-3 py-1.5 text-sm ${
                    active ? "bg-ink text-sand" : "hover:bg-white"
                  } ${disabled ? "pointer-events-none opacity-60" : ""}`}
                >
                  <bdi className="truncate font-bold">{c.title}</bdi>
                  <span className={active ? "text-sand/80" : "text-mud"}>{updatedAr(c.updated_at)}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </nav>
  );
}
