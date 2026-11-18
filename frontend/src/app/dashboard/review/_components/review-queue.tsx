"use client";

import Link from "next/link";
import { type FormEvent, useCallback, useEffect, useId, useRef, useState } from "react";
import { PageSkeleton, RetryAlert } from "@/app/_components/page-status";
import { EvidencePanel } from "@/components/evidence-panel";
import { ApiError, type Finding, request } from "@/lib/api";
import { damageTypeAr, severityAr } from "@/lib/labels";
import { useMeState } from "@/lib/use-me";

const DECISIONS = [
  { value: "confirm", label: "تأكيد" },
  { value: "correct", label: "تأكيد مع تصحيح" },
  { value: "reject", label: "رفض" },
] as const;

type Decision = (typeof DECISIONS)[number]["value"];

const FIELD_CLASS = "min-h-11 rounded-lg border border-mud/60 bg-white px-3 disabled:opacity-50";

export function ReviewQueue() {
  const { me, error: meError, retry: retryMe } = useMeState();
  const [queue, setQueue] = useState<Finding[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState("");
  const pendingFocus = useRef<number | null>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const items = useRef<(HTMLElement | null)[]>([]);

  const load = useCallback(() => {
    return request<Finding[]>("/review-queue").then(setQueue, (e) =>
      setError(e instanceof ApiError ? e.message : "تعذر تحميل قائمة المراجعة."),
    );
  }, []);

  useEffect(() => {
    if (me) load();
  }, [me, load]);

  useEffect(() => {
    if (pendingFocus.current === null || queue === null) return;
    const next = items.current[Math.min(pendingFocus.current, queue.length - 1)];
    (next ?? heading.current)?.focus();
    pendingFocus.current = null;
  }, [queue]);

  function reload() {
    setError(null);
    load();
  }

  function decided(index: number) {
    setNotice("حُفظ القرار وأُزيل البلاغ من القائمة.");
    pendingFocus.current = index;
    reload();
  }

  if (meError) {
    return (
      <div className="pt-6">
        <RetryAlert message={meError} onRetry={retryMe} />
      </div>
    );
  }
  if (queue === null && error) {
    return (
      <div className="pt-6">
        <RetryAlert message={error} onRetry={reload} />
      </div>
    );
  }
  if (!me || queue === null) return <PageSkeleton />;

  return (
    <div className="flex flex-col gap-4 pt-2">
      <h1 ref={heading} tabIndex={-1} className="text-3xl font-bold leading-snug">
        بانتظار المراجعة ({queue.length.toLocaleString("ar-SA")})
      </h1>
      <p role="status" className="text-sm empty:hidden">
        {notice}
      </p>
      {error && <RetryAlert message={error} onRetry={reload} />}
      {queue.length === 0 ? (
        <div className="flex flex-col items-start gap-2 rounded-xl bg-white/75 p-4">
          <p className="leading-relaxed">لا بلاغات بانتظار المراجعة. تصل البلاغات الجديدة من صور الزوار.</p>
          <Link href="/dashboard/maps" className="font-bold text-sadu underline underline-offset-4">
            راجع مخططات التلف بانتظار الاعتماد
          </Link>
        </div>
      ) : (
        queue.map((finding, index) => (
          <ReviewItem
            key={finding.id}
            ref={(element) => {
              items.current[index] = element;
            }}
            finding={finding}
            onDecided={() => decided(index)}
          />
        ))
      )}
    </div>
  );
}

function ReviewItem({
  finding,
  onDecided,
  ref,
}: {
  finding: Finding;
  onDecided: () => void;
  ref: (element: HTMLElement | null) => void;
}) {
  const [decision, setDecision] = useState<Decision | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const id = useId();
  const correcting = decision === "correct";

  async function decide(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setPending(true);
    setError(null);
    try {
      await request(`/findings/${finding.id}/review`, {
        method: "POST",
        body: JSON.stringify({
          decision,
          reason: form.get("reason"),
          damage_type: correcting ? form.get("damage_type") : undefined,
          severity: correcting ? form.get("severity") : undefined,
        }),
      });
      onDecided();
    } catch {
      setError("تعذر حفظ القرار. اختيارك ما زال هنا، أعد المحاولة.");
    } finally {
      setPending(false);
    }
  }

  return (
    <article
      ref={ref}
      tabIndex={-1}
      aria-label={`${damageTypeAr[finding.damage_type] ?? finding.damage_type} · ${severityAr[finding.severity]}`}
      className="flex flex-col gap-3 rounded-xl bg-white/75 p-4"
    >
      <EvidencePanel finding={finding} />
      <form onSubmit={decide} className="flex flex-col gap-4 text-sm">
        <fieldset className="flex flex-col gap-2">
          <legend className="mb-1 font-bold">القرار</legend>
          <div className="flex flex-wrap gap-x-5 gap-y-1">
            {DECISIONS.map((option) => (
              <label key={option.value} className="flex min-h-11 items-center gap-2">
                <input
                  type="radio"
                  name="decision"
                  value={option.value}
                  required
                  checked={decision === option.value}
                  onChange={() => setDecision(option.value)}
                  className="size-5 accent-sadu"
                />
                {option.label}
              </label>
            ))}
          </div>
        </fieldset>
        <div className="flex flex-wrap gap-3">
          <label className="flex flex-col gap-1">
            <span className="text-mud">نوع التلف</span>
            <select
              name="damage_type"
              defaultValue={finding.damage_type}
              disabled={!correcting}
              aria-describedby={correcting ? undefined : `${id}-correct-hint`}
              className={FIELD_CLASS}
            >
              {Object.entries(damageTypeAr).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-mud">الشدة</span>
            <select
              name="severity"
              defaultValue={finding.severity}
              disabled={!correcting}
              aria-describedby={correcting ? undefined : `${id}-correct-hint`}
              className={FIELD_CLASS}
            >
              {Object.entries(severityAr).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
        </div>
        {!correcting && (
          <p id={`${id}-correct-hint`} className="-mt-2 text-mud">
            اختر «تأكيد مع تصحيح» لتعديل النوع أو الشدة.
          </p>
        )}
        <label className="flex flex-col gap-1">
          <span className="font-bold">سبب القرار</span>
          <textarea
            name="reason"
            required
            maxLength={1000}
            rows={3}
            className="rounded-lg border border-mud/60 bg-white p-3 leading-relaxed"
          />
        </label>
        {error && (
          <p role="alert" className="rounded-xl border border-urgent/40 bg-urgent/10 p-3">
            {error}
          </p>
        )}
        <button
          type="submit"
          disabled={pending}
          className="min-h-11 self-start rounded-full bg-sadu px-6 font-bold text-sand hover:bg-ink disabled:opacity-50"
        >
          {pending ? "نعتمد القرار…" : "اعتمد القرار"}
        </button>
      </form>
    </article>
  );
}
