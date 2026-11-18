"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ApiError, type Site } from "@/lib/api";
import { type IngestJob, type UploadBatch, assignFacade, batchSettled, getBatch, retryJob } from "@/lib/ingest";
import { jobStatusAr } from "@/lib/labels";
import { countAr, photos as photoForms } from "@/lib/plural";

const POLL_MS = 2000;

const STATUS_CLASS: Record<IngestJob["status"], string> = {
  queued: "bg-clay/25 text-ink",
  analysing: "bg-watch/25 text-ink",
  needs_facade: "border border-mud/60 text-mud",
  done: "bg-ink text-sand",
  failed: "bg-urgent/15 text-urgent",
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
      <div className="flex flex-col gap-1">
        <h2 id="batch-heading" className="text-xl font-bold">
          {countAr(batch.total, photoForms)}
        </h2>
        <p role="status" className="text-mud">
          {settled ? "انتهت المعالجة. " : "نحلّل الصور واحدة تلو الأخرى… "}
          اكتمل <strong className="tabular-nums text-ink">{done.toLocaleString("ar-SA")}</strong> من{" "}
          <span className="tabular-nums">{batch.total.toLocaleString("ar-SA")}</span>
        </p>
        <div className="h-1.5 overflow-hidden rounded-full bg-clay/25" aria-hidden>
          <div className="h-full rounded-full bg-sadu" style={{ inlineSize: `${(done / Math.max(batch.total, 1)) * 100}%` }} />
        </div>
        {pollError && (
          <p role="alert" className="text-sm text-urgent">
            {pollError}
          </p>
        )}
      </div>

      <ul className="flex flex-col gap-2">
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
    <article className="flex flex-wrap items-center gap-3 rounded-xl bg-white/75 p-3">
      {job.photo_url ? (
        <img src={job.photo_url} alt="" className="h-14 w-20 shrink-0 rounded-lg object-cover" />
      ) : (
        <div aria-hidden className="h-14 w-20 shrink-0 rounded-lg bg-clay/20" />
      )}
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <bdi className="truncate font-bold">{job.file_name}</bdi>
        <p className="flex flex-wrap items-center gap-2 text-sm">
          <span className={`rounded-full px-2.5 py-0.5 text-xs font-bold ${STATUS_CLASS[job.status]}`}>
            {jobStatusAr[job.status]}
          </span>
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
        <Link
          href={`/dashboard/maps/${job.map_id}`}
          className="inline-flex min-h-11 items-center rounded-full bg-sadu px-4 text-sm font-bold text-sand hover:bg-ink"
        >
          افتح المخطط
        </Link>
      )}

      {job.can_retry && (
        <button
          type="button"
          disabled={busy}
          onClick={() => act(() => retryJob(job.id))}
          className="min-h-11 rounded-full border border-ink/30 px-4 text-sm hover:bg-ink hover:text-sand disabled:opacity-50"
        >
          أعد المحاولة
        </button>
      )}

      {job.status === "needs_facade" && (
        <form
          className="flex flex-wrap items-end gap-2"
          onSubmit={(event) => {
            event.preventDefault();
            if (facadeId) act(() => assignFacade(job.id, facadeId));
          }}
        >
          <label className="flex flex-col gap-1 text-sm">
            <span>واجهة الصورة</span>
            <select
              required
              value={facadeId}
              onChange={(e) => setFacadeId(e.target.value)}
              className="min-h-11 rounded-lg border border-mud/60 bg-white px-3 text-base"
            >
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
            </select>
          </label>
          <button
            type="submit"
            disabled={busy || !facadeId}
            className="min-h-11 rounded-full bg-ink px-4 text-sm font-bold text-sand hover:bg-sadu disabled:opacity-50"
          >
            حلّل على هذه الواجهة
          </button>
        </form>
      )}
    </article>
  );
}
