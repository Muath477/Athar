"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { StoryView } from "./story-view";
import { type ObservationState, request } from "@/lib/api";
import { followObservation } from "@/lib/events";
import { damageTypeAr, findingLabelAr, retakeAr, severityAr, stageAr } from "@/lib/labels";

export function ObservationProgress() {
  const id = useSearchParams().get("id");
  const [state, setState] = useState<ObservationState | null>(null);
  const [answering, setAnswering] = useState(false);

  useEffect(() => {
    if (!id) return;
    return followObservation(id, setState);
  }, [id]);

  async function answer(facadeId: string | null) {
    if (!id) return;
    setAnswering(true);
    await request(`/observations/${id}/answers`, {
      method: "POST",
      body: JSON.stringify({ question_id: "which_facade", facade_id: facadeId }),
    });
    setState({ status: "processing", detail: { stage: "answered" } });
    setAnswering(false);
  }

  if (!id) return <p className="pt-6">لا توجد صورة لعرضها.</p>;
  if (!state || state.status === "received" || state.status === "processing") {
    return (
      <div className="flex flex-col items-center gap-4 pt-16" aria-live="polite">
        <div className="sadu-band w-40 animate-pulse" aria-hidden />
        <p className="text-lg">{stageAr[state?.detail.stage ?? ""] ?? "استلمنا صورتك"}</p>
      </div>
    );
  }

  const { status, detail } = state;
  if (status === "needs_input") {
    return (
      <div className="flex flex-col gap-4 pt-6">
        <h1 className="text-xl font-bold">أي واجهة صوّرت؟</h1>
        <div className="grid grid-cols-2 gap-3">
          {detail.options?.map((o) => (
            <button
              key={o.facade_id}
              disabled={answering}
              onClick={() => answer(o.facade_id)}
              className="rounded-xl border border-ink bg-white/70 p-4"
            >
              {o.name_ar}
            </button>
          ))}
        </div>
        <button disabled={answering} onClick={() => answer(null)} className="self-start text-sm underline">
          لا أعرف
        </button>
      </div>
    );
  }
  if (status === "failed") {
    return <p className="pt-6">حدث خطأ أثناء معالجة صورتك. لم يُنشر شيء منها.</p>;
  }
  if (detail.site_found === false) {
    return <p className="pt-6">لم نجد مبنى تراثيًا مسجلًا قريبًا من موقعك.</p>;
  }

  return (
    <div className="flex flex-col gap-5 pt-4" aria-live="polite">
      {detail.retake_reason && (
        <section className="flex flex-col gap-2 rounded-xl border border-moderate bg-moderate/10 p-4">
          <p>{retakeAr[detail.retake_reason] ?? "نحتاج صورة أوضح للمقارنة."}</p>
          <Link href="/capture" className="self-start rounded-full bg-mud px-5 py-2 text-sand">
            أعد التصوير
          </Link>
        </section>
      )}
      {detail.findings && detail.findings.length > 0 && (
        <section className="rounded-xl bg-white/70 p-4">
          <h2 className="mb-2 font-bold">شكرًا، صورتك ساعدت</h2>
          <ul className="flex flex-col gap-1 text-sm">
            {detail.findings.map((f) => (
              <li key={f.id}>
                {damageTypeAr[f.damage_type] ?? f.damage_type} · {severityAr[f.severity]} ·{" "}
                {f.status === "published" ? findingLabelAr[f.label] : "بانتظار مراجعة خبير"}
              </li>
            ))}
          </ul>
        </section>
      )}
      {detail.passport_stamped && (
        <p className="text-sm">
          أُضيف ختم هذا المبنى إلى <Link href="/passport" className="underline">جوازك</Link>.
        </p>
      )}
      <StoryView storyId={detail.story_id ?? null} />
    </div>
  );
}
