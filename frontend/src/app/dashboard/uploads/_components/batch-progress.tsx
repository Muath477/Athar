"use client";

import { RotateCwIcon, TriangleAlertIcon } from "lucide-react";
import Link from "next/link";
import { type ComponentProps, useEffect, useId, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";
import { Progress } from "@/components/ui/progress";
import { ApiError, type Site } from "@/lib/api";
import { type IngestJob, type UploadBatch, assignFacade, batchSettled, getBatch, retryJob } from "@/lib/ingest";
import { jobStatusAr } from "@/lib/labels";
import { countAr, photos as photoForms } from "@/lib/plural";

const POLL_MS = 2000;

const STATUS_BADGE: Record<IngestJob["status"], ComponentProps<typeof Badge>["variant"]> = {
  queued: "muted",
  analysing: "outline",
  needs_facade: "outline",
  done: "ink",
  failed: "urgent",
};

export function BatchProgress({ initial, sites }: { initial: UploadBatch; sites: Site[] }) {
  const [batch, setBatch] = useState(initial);
  const [pollError, setPollError] = useState<string | null>(null);
  const [round, setRound] = useState(0);
  const settled = batchSettled(batch);

  useEffect(() => {
    if (settled) return;
    const timer = window.setTimeout(() => {
      getBatch(batch.id).then(
        (next) => {
          setBatch(next);
          setPollError(null);
          setRound((n) => n + 1);
        },
        () => {
          setPollError("انقطع تحديث الحالة. نعيد المحاولة تلقائيًا.");
          setRound((n) => n + 1);
        },
      );
    }, POLL_MS);
    return () => window.clearTimeout(timer);
  }, [batch.id, settled, round]);

  function replace(job: IngestJob) {
    setBatch((current) => ({ ...current, jobs: current.jobs.map((j) => (j.id === job.id ? job : j)) }));
  }

  const done = batch.jobs.filter((j) => j.status === "done").length;

  return (
    <section aria-labelledby="batch-heading" className="flex flex-col gap-4">
      <div className="flex flex-col gap-2">
        <h2 id="batch-heading" className="text-xl font-bold">
          {countAr(batch.total, photoForms)}
        </h2>
        <p role="status" className="text-mud">
          {settled ? "انتهت المعالجة. " : "نحلّل الصور واحدة تلو الأخرى… "}
          اكتمل <strong className="tabular-nums text-ink">{done.toLocaleString("ar-SA")}</strong> من{" "}
          <span className="tabular-nums">{batch.total.toLocaleString("ar-SA")}</span>
        </p>
        <Progress
          value={(done / Math.max(batch.total, 1)) * 100}
          aria-labelledby="batch-heading"
          className="max-w-md"
        />
        {pollError && (
          <p role="alert" className="text-sm text-urgent">
            {pollError}
          </p>
        )}
      </div>

      <ul className="flex flex-col divide-y divide-line rounded-sm border border-line bg-white">
        {batch.jobs.map((job) => (
          <li key={job.id}>
            <JobRow job={job} sites={sites} onChange={replace} />
          </li>
        ))}
      </ul>
    </section>
  );
}

function JobRow({ job, sites, onChange }: { job: IngestJob; sites: Site[]; onChange: (job: IngestJob) => void }) {
  const [facadeId, setFacadeId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const facadeSelectId = useId();
  const candidateSites = sites.filter((s) => !job.site_id || s.id === job.site_id);

  async function act(action: () => Promise<IngestJob>) {
    setBusy(true);
    setError(null);
    try {
      onChange(await action());
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "تعذر تنفيذ الطلب. أعد المحاولة.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <article className="flex flex-wrap items-center gap-3 p-3">
      {job.photo_url ? (
        <img src={job.photo_url} alt="" className="h-14 w-20 shrink-0 rounded-sm object-cover" />
      ) : (
        <div aria-hidden className="h-14 w-20 shrink-0 rounded-sm bg-clay/60" />
      )}
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <bdi className="truncate font-bold">{job.file_name}</bdi>
        <p className="flex flex-wrap items-center gap-2 text-sm">
          <Badge variant={STATUS_BADGE[job.status]}>
            {job.status === "failed" && <TriangleAlertIcon aria-hidden="true" />}
            {jobStatusAr[job.status]}
          </Badge>
          {job.facade_match === "gps" && <span className="text-mud">طابقنا الواجهة من إحداثيات الصورة</span>}
        </p>
        {job.error_ar && <p className="text-sm text-urgent">{job.error_ar}</p>}
        {error && (
          <p role="alert" className="text-sm text-urgent">
            {error}
          </p>
        )}
      </div>

      {job.status === "done" && job.map_id && (
        <Link href={`/dashboard/maps/${job.map_id}`} className={buttonVariants({ variant: "outline", size: "sm" })}>
          افتح المخطط
        </Link>
      )}

      {job.can_retry && (
        <Button type="button" variant="outline" size="sm" disabled={busy} onClick={() => act(() => retryJob(job.id))}>
          <RotateCwIcon aria-hidden="true" />
          أعد المحاولة
        </Button>
      )}

      {job.status === "needs_facade" && (
        <form
          className="flex w-full flex-wrap items-end gap-2 sm:w-auto"
          onSubmit={(event) => {
            event.preventDefault();
            if (facadeId) act(() => assignFacade(job.id, facadeId));
          }}
        >
          <div className="flex min-w-48 flex-1 flex-col gap-1.5">
            <Label htmlFor={facadeSelectId}>واجهة الصورة</Label>
            <NativeSelect id={facadeSelectId} required value={facadeId} onChange={(e) => setFacadeId(e.target.value)}>
              <option value="" disabled>
                اختر الواجهة
              </option>
              {candidateSites.map((site) => (
                <optgroup key={site.id} label={site.name_ar}>
                  {site.facades.map((facade) => (
                    <option key={facade.id} value={facade.id}>
                      {facade.name_ar}
                    </option>
                  ))}
                </optgroup>
              ))}
            </NativeSelect>
          </div>
          <Button type="submit" size="sm" disabled={busy || !facadeId}>
            حلّل على هذه الواجهة
          </Button>
        </form>
      )}
    </article>
  );
}
