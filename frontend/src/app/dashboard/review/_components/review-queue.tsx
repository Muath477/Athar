"use client";

import Link from "next/link";
import { type FormEvent, useCallback, useEffect, useId, useRef, useState } from "react";
import { PageSkeleton, RetryAlert } from "@/app/_components/page-status";
import { EvidencePanel } from "@/components/evidence-panel";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, type Finding, request } from "@/lib/api";
import { damageTypeAr, severityAr } from "@/lib/labels";
import { useMeState } from "@/lib/use-me";

const DECISIONS = [
  { value: "confirm", label: "تأكيد" },
  { value: "correct", label: "تأكيد مع تصحيح" },
  { value: "reject", label: "رفض" },
] as const;

type Decision = (typeof DECISIONS)[number]["value"];

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
      <h1 ref={heading} tabIndex={-1} className="text-3xl font-bold">
        بانتظار المراجعة ({queue.length.toLocaleString("ar-SA")})
      </h1>
      <p role="status" className="text-sm empty:hidden">
        {notice}
      </p>
      {error && <RetryAlert message={error} onRetry={reload} />}
      {queue.length === 0 ? (
        <div className="flex flex-col items-start gap-2 rounded-sm border border-line bg-white p-4">
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
    if (!decision) {
      setError("اختر القرار أولًا: تأكيد أو تصحيح أو رفض.");
      return;
    }
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
      className="flex flex-col gap-3 rounded-sm border border-line bg-white p-4"
    >
      <EvidencePanel finding={finding} />
      <form onSubmit={decide} className="flex flex-col gap-4 text-sm">
        <fieldset className="flex flex-col gap-2">
          <legend className="mb-1 font-bold">القرار</legend>
          <RadioGroup
            name="decision"
            required
            value={decision ?? ""}
            onValueChange={(value) => setDecision(value as Decision)}
            className="flex flex-wrap gap-x-5 gap-y-1"
          >
            {DECISIONS.map((option) => (
              <div key={option.value} className="flex min-h-11 items-center gap-2">
                <RadioGroupItem id={`${id}-${option.value}`} value={option.value} />
                <Label htmlFor={`${id}-${option.value}`} className="text-ink">
                  {option.label}
                </Label>
              </div>
            ))}
          </RadioGroup>
        </fieldset>
        <div className="flex flex-wrap gap-3">
          <label className="flex flex-col gap-1">
            <span className="text-mud">نوع التلف</span>
            <NativeSelect
              name="damage_type"
              defaultValue={finding.damage_type}
              disabled={!correcting}
              aria-describedby={correcting ? undefined : `${id}-correct-hint`}
            >
              {Object.entries(damageTypeAr).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </NativeSelect>
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-mud">الشدة</span>
            <NativeSelect
              name="severity"
              defaultValue={finding.severity}
              disabled={!correcting}
              aria-describedby={correcting ? undefined : `${id}-correct-hint`}
            >
              {Object.entries(severityAr).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </NativeSelect>
          </label>
        </div>
        {!correcting && (
          <p id={`${id}-correct-hint`} className="-mt-2 text-mud">
            اختر «تأكيد مع تصحيح» لتعديل النوع أو الشدة.
          </p>
        )}
        <label className="flex flex-col gap-1">
          <span className="font-bold">سبب القرار</span>
          <Textarea name="reason" required maxLength={1000} rows={3} />
        </label>
        {error && (
          <p role="alert" className="rounded-sm border border-urgent/40 bg-urgent/5 p-3">
            {error}
          </p>
        )}
        <Button type="submit" disabled={pending} className="self-start">
          {pending ? "نعتمد القرار…" : "اعتمد القرار"}
        </Button>
      </form>
    </article>
  );
}
