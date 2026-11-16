"use client";

import { useCallback, useEffect, useState } from "react";
import { EvidencePanel } from "@/components/dashboard/evidence-panel";
import { ApiError, type Finding, request } from "@/lib/api";
import { damageTypeAr, severityAr } from "@/lib/labels";
import { useMe } from "@/lib/use-me";

export function ReviewQueue() {
  const me = useMe();
  const [queue, setQueue] = useState<Finding[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    () =>
      request<Finding[]>("/review-queue").then(setQueue, (e) =>
        setError(e instanceof ApiError ? e.message : "تعذر تحميل القائمة."),
      ),
    [],
  );

  useEffect(() => {
    if (me) load();
  }, [me, load]);

  if (!me || queue === null) return <p className="pt-6">{error ?? "…"}</p>;

  return (
    <div className="flex flex-col gap-4 pt-2">
      <h1 className="text-2xl font-bold">بانتظار المراجعة ({queue.length})</h1>
      {queue.length === 0 && <p>لا شيء بانتظارك الآن.</p>}
      {queue.map((finding) => (
        <ReviewItem key={finding.id} finding={finding} onDone={load} />
      ))}
    </div>
  );
}

function ReviewItem({ finding, onDone }: { finding: Finding; onDone: () => Promise<void> }) {
  const [pending, setPending] = useState(false);

  async function decide(form: FormData) {
    setPending(true);
    const decision = form.get("decision");
    await request(`/findings/${finding.id}/review`, {
      method: "POST",
      body: JSON.stringify({
        decision,
        reason: form.get("reason"),
        damage_type: decision === "correct" ? form.get("damage_type") : undefined,
        severity: decision === "correct" ? form.get("severity") : undefined,
      }),
    });
    await onDone();
    setPending(false);
  }

  return (
    <article className="flex flex-col gap-3 rounded-xl border border-clay/40 p-3">
      <EvidencePanel finding={finding} />
      <form action={decide} className="flex flex-col gap-2 text-sm">
        <div className="flex flex-wrap gap-4">
          {[
            ["confirm", "تأكيد"],
            ["correct", "تأكيد مع تصحيح"],
            ["reject", "رفض"],
          ].map(([value, label]) => (
            <label key={value} className="flex items-center gap-1">
              <input type="radio" name="decision" value={value} required /> {label}
            </label>
          ))}
        </div>
        <div className="flex flex-wrap gap-2">
          <select name="damage_type" defaultValue={finding.damage_type} className="rounded border p-1">
            {Object.entries(damageTypeAr).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
          <select name="severity" defaultValue={finding.severity} className="rounded border p-1">
            {Object.entries(severityAr).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>
        <textarea name="reason" required maxLength={1000} placeholder="سبب القرار" className="rounded border p-2" />
        <button disabled={pending} className="self-start rounded-full bg-ink px-5 py-1.5 text-sand">
          {pending ? "…" : "اعتمد القرار"}
        </button>
      </form>
    </article>
  );
}
