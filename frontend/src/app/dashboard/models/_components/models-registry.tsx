"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { PageSkeleton, RetryAlert } from "@/app/_components/page-status";
import { ApiError, can, request } from "@/lib/api";
import {
  type DamageModel,
  ML_DOCS_URL,
  NOTEBOOK_URL,
  metricLines,
  modelStatusAr,
  sortModels,
} from "@/lib/models";
import { countAr, modelVersions } from "@/lib/plural";
import { useMeState } from "@/lib/use-me";

const STATUS_CLASS: Record<DamageModel["status"], string> = {
  active: "bg-sadu text-sand",
  candidate: "bg-watch/30 text-ink",
  retired: "bg-clay/30 text-mud",
};

export function ModelsRegistry() {
  const { me, error: meError, retry: retryMe } = useMeState();
  const [models, setModels] = useState<DamageModel[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState("");
  const allowed = can(me, "manage_models");

  const load = useCallback(() => {
    return request<DamageModel[]>("/ml/models").then(
      (list) => setModels(sortModels(list)),
      (e) => setError(e instanceof ApiError ? e.message : "تعذر تحميل سجل النماذج."),
    );
  }, []);

  useEffect(() => {
    if (allowed) load();
  }, [allowed, load]);

  function reload() {
    setError(null);
    load();
  }

  function activated(model: DamageModel) {
    setNotice(`فُعّل الإصدار ${model.version}، وتستخدمه التحليلات الجديدة من الآن.`);
    reload();
  }

  if (meError) {
    return (
      <div className="pt-6">
        <RetryAlert message={meError} onRetry={retryMe} />
      </div>
    );
  }
  if (!me) return <PageSkeleton />;
  if (!allowed) {
    return (
      <p role="alert" className="pt-6">
        هذه الصفحة لمهندسي النماذج فقط.
      </p>
    );
  }
  if (models === null && error) {
    return (
      <div className="pt-6">
        <RetryAlert message={error} onRetry={reload} />
      </div>
    );
  }
  if (models === null) return <PageSkeleton />;

  return (
    <div className="flex flex-col gap-4 pt-2">
      <h1 className="text-3xl font-bold leading-snug">نموذج تحليل التلف</h1>
      <p className="max-w-prose leading-relaxed text-mud">
        يدرَّب النموذج على المخططات المعتمدة من المختصين، ويُفعَّل إصدار واحد فقط في كل مرة. يبقى كل مخطط
        يحلله النموذج مسودة حتى يراجعه المختص ميدانيًا ويعتمده.
      </p>
      <p className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
        <a href={NOTEBOOK_URL} target="_blank" rel="noreferrer" className="font-bold text-sadu underline underline-offset-4">
          افتح دفتر التدريب
        </a>
        <a href={ML_DOCS_URL} target="_blank" rel="noreferrer" className="font-bold text-sadu underline underline-offset-4">
          اقرأ شرح مسار البيانات والتقييم
        </a>
      </p>
      <p role="status" className="text-sm empty:hidden">
        {notice}
      </p>
      {error && <RetryAlert message={error} onRetry={reload} />}
      <h2 className="text-lg font-bold">{countAr(models.length, modelVersions)}</h2>
      {models.length === 0 ? (
        <p className="rounded-xl bg-white/75 p-4 leading-relaxed">
          سجّل أول إصدار بعد تدريبه وتقييمه في الدفتر، وسيظهر هنا مع نتائجه.
        </p>
      ) : (
        <ul className="flex flex-col gap-3">
          {models.map((model) => (
            <li key={model.id}>
              <ModelCard model={model} onActivated={() => activated(model)} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function ModelCard({ model, onActivated }: { model: DamageModel; onActivated: () => void }) {
  const [confirming, setConfirming] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const cancelRef = useRef<HTMLButtonElement>(null);
  const metrics = metricLines(model.metrics);

  useEffect(() => {
    if (confirming) cancelRef.current?.focus();
  }, [confirming]);

  async function activate() {
    setConfirming(false);
    setPending(true);
    setError(null);
    try {
      await request(`/ml/models/${model.id}/activate`, { method: "POST" });
      onActivated();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "تعذر تفعيل الإصدار. أعد المحاولة.");
    } finally {
      setPending(false);
    }
  }

  return (
    <article aria-label={`${model.name} ${model.version}`} className="flex flex-col gap-3 rounded-xl bg-white/75 p-4">
      <div className="flex flex-wrap items-center gap-3">
        <h3 className="text-lg font-bold">
          <bdi>{model.name}</bdi> · الإصدار <bdi>{model.version}</bdi>
        </h3>
        <span className={`rounded-full px-3 py-1 text-xs font-bold ${STATUS_CLASS[model.status]}`}>
          {modelStatusAr[model.status]}
        </span>
      </div>
      <dl className="grid gap-x-6 gap-y-1 text-sm sm:grid-cols-[auto_1fr]">
        <dt className="text-mud">النموذج الأساسي</dt>
        <dd>
          <bdi>{model.base_model}</bdi>
        </dd>
        <dt className="text-mud">موقع الأوزان</dt>
        <dd className="break-all">
          <bdi>{model.adapter_uri}</bdi>
        </dd>
        <dt className="text-mud">سُجّل يوم</dt>
        <dd>
          <time dateTime={model.created_at}>{new Date(model.created_at).toLocaleDateString("ar-SA")}</time>
        </dd>
      </dl>
      {metrics.length > 0 && (
        <table className="w-full max-w-md text-sm">
          <caption className="text-start font-bold">نتائج التقييم على مجموعة الاختبار</caption>
          <tbody>
            {metrics.map((line) => (
              <tr key={line.key} className="border-b border-clay/30">
                <th scope="row" className="py-1 pe-4 text-start font-normal text-mud">
                  <bdi>{line.label}</bdi>
                </th>
                <td className="py-1">{line.value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {model.status !== "active" && (
        <div className="flex flex-wrap items-center gap-2">
          {confirming ? (
            <div role="group" aria-label="تأكيد التفعيل" className="flex flex-wrap items-center gap-2">
              <p className="w-full text-sm font-bold">
                سيحل هذا الإصدار محل الإصدار المفعل في كل تحليل جديد، ويخرج السابق من الخدمة.
              </p>
              <button
                type="button"
                onClick={activate}
                className="min-h-11 rounded-full bg-sadu px-5 text-sm font-bold text-sand hover:bg-ink"
              >
                فعّل الإصدار
              </button>
              <button
                ref={cancelRef}
                type="button"
                onClick={() => setConfirming(false)}
                className="min-h-11 rounded-full border border-ink/30 px-5 text-sm hover:bg-ink hover:text-sand"
              >
                إلغاء
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setConfirming(true)}
              disabled={pending}
              className="min-h-11 rounded-full bg-ink px-5 text-sm font-bold text-sand disabled:opacity-40"
            >
              {pending ? "نفعّل الإصدار…" : "فعّل هذا الإصدار"}
            </button>
          )}
        </div>
      )}
      {error && (
        <p role="alert" className="text-sm text-urgent">
          {error}
        </p>
      )}
    </article>
  );
}
