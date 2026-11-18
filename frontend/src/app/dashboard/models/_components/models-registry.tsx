"use client";

import { type ComponentProps, type MouseEvent, useCallback, useEffect, useState } from "react";
import { PageSkeleton, RetryAlert } from "@/app/_components/page-status";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ApiError, can, request } from "@/lib/api";
import {
  type DamageModel,
  ML_DOCS_URL,
  type MetricColumn,
  NOTEBOOK_URL,
  metricColumns,
  metricLines,
  modelStatusAr,
  sortModels,
} from "@/lib/models";
import { countAr, modelVersions } from "@/lib/plural";
import { useMeState } from "@/lib/use-me";

const STATUS_BADGE: Record<DamageModel["status"], ComponentProps<typeof Badge>["variant"]> = {
  active: "default",
  candidate: "outline",
  retired: "muted",
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
      <p role="alert" className="mt-6 rounded-sm border border-line bg-white p-3">
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
    <div className="flex flex-col gap-5 pt-2">
      <h1 className="text-3xl font-bold">نموذج تحليل التلف</h1>
      <p className="max-w-prose leading-relaxed text-mud">
        يدرَّب النموذج على المخططات المعتمدة من المختصين، ويُفعَّل إصدار واحد فقط في كل مرة. يبقى كل مخطط يحلله النموذج
        مسودة حتى يراجعه المختص ميدانيًا ويعتمده.
      </p>
      <p className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
        <a
          href={NOTEBOOK_URL}
          target="_blank"
          rel="noreferrer"
          className="font-bold text-sadu underline underline-offset-4"
        >
          افتح دفتر التدريب
        </a>
        <a
          href={ML_DOCS_URL}
          target="_blank"
          rel="noreferrer"
          className="font-bold text-sadu underline underline-offset-4"
        >
          اقرأ شرح مسار البيانات والتقييم
        </a>
      </p>
      <p role="status" className="text-sm empty:hidden">
        {notice}
      </p>
      {error && <RetryAlert message={error} onRetry={reload} />}
      {models.length === 0 ? (
        <p className="rounded-sm border border-line bg-white p-4 leading-relaxed">
          سجّل أول إصدار بعد تدريبه وتقييمه في الدفتر، وسيظهر هنا مع نتائجه.
        </p>
      ) : (
        <VersionsTable models={models} onActivated={activated} />
      )}
    </div>
  );
}

function VersionsTable({ models, onActivated }: { models: DamageModel[]; onActivated: (model: DamageModel) => void }) {
  const columns = metricColumns(models);

  return (
    <section aria-labelledby="versions-heading" className="flex flex-col gap-2">
      <div className="flex flex-wrap items-baseline gap-x-3">
        <h2 id="versions-heading" className="text-lg font-bold">
          {countAr(models.length, modelVersions)}
        </h2>
        {columns.length > 0 && <p className="text-sm text-mud">النتائج على مجموعة الاختبار</p>}
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>الإصدار</TableHead>
            <TableHead>الحالة</TableHead>
            {columns.map((column) => (
              <TableHead key={column.key}>
                <bdi>{column.label}</bdi>
              </TableHead>
            ))}
            <TableHead>سُجّل يوم</TableHead>
            <TableHead>
              <span className="sr-only">الإجراءات</span>
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {models.map((model) => (
            <VersionRow key={model.id} model={model} columns={columns} onActivated={() => onActivated(model)} />
          ))}
        </TableBody>
      </Table>
    </section>
  );
}

function VersionRow({
  model,
  columns,
  onActivated,
}: {
  model: DamageModel;
  columns: MetricColumn[];
  onActivated: () => void;
}) {
  const [confirming, setConfirming] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const values = new Map(metricLines(model.metrics).map((line) => [line.key, line.value]));

  async function activate(event: MouseEvent<HTMLButtonElement>) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      await request(`/ml/models/${model.id}/activate`, { method: "POST" });
      setConfirming(false);
      onActivated();
    } catch (e) {
      setConfirming(false);
      setError(e instanceof ApiError ? e.message : "تعذر تفعيل الإصدار. أعد المحاولة.");
    } finally {
      setPending(false);
    }
  }

  return (
    <TableRow className={model.status === "active" ? "bg-sand" : undefined}>
      <TableCell className="min-w-56">
        <div className="flex flex-col gap-0.5">
          <span className="font-bold">
            <bdi>{model.name}</bdi> · <bdi>{model.version}</bdi>
          </span>
          <span className="text-xs text-mud">
            النموذج الأساسي <bdi>{model.base_model}</bdi>
          </span>
          <span className="text-xs break-all text-mud">
            الأوزان <bdi>{model.adapter_uri}</bdi>
          </span>
        </div>
      </TableCell>
      <TableCell>
        <Badge variant={STATUS_BADGE[model.status]}>{modelStatusAr[model.status]}</Badge>
      </TableCell>
      {columns.map((column) => (
        <TableCell key={column.key} className="whitespace-nowrap">
          {values.get(column.key) ?? <span className="text-mud">—</span>}
        </TableCell>
      ))}
      <TableCell className="whitespace-nowrap">
        <time dateTime={model.created_at}>{new Date(model.created_at).toLocaleDateString("ar-SA")}</time>
      </TableCell>
      <TableCell className="text-end">
        {model.status !== "active" && (
          <AlertDialog open={confirming} onOpenChange={setConfirming}>
            <AlertDialogTrigger asChild>
              <Button type="button" variant="outline" size="sm" disabled={pending}>
                {pending ? "نفعّل الإصدار…" : "فعّل هذا الإصدار"}
                <span className="sr-only">
                  {" "}
                  <bdi>{model.version}</bdi>
                </span>
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>
                  فعّل الإصدار <bdi>{model.version}</bdi>؟
                </AlertDialogTitle>
                <AlertDialogDescription>
                  سيحل هذا الإصدار محل الإصدار المفعل في كل تحليل جديد، ويخرج السابق من الخدمة.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogAction disabled={pending} onClick={activate}>
                  فعّل الإصدار
                </AlertDialogAction>
                <AlertDialogCancel>إلغاء</AlertDialogCancel>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        )}
        {error && (
          <p role="alert" className="mt-1 text-start text-sm text-urgent">
            {error}
          </p>
        )}
      </TableCell>
    </TableRow>
  );
}
