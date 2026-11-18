"use client";

import Link from "next/link";
import { useState } from "react";
import { ApiError } from "@/lib/api";
import { type Device, type IngestJob, captureNow, deleteDevice, deviceHistory } from "@/lib/ingest";
import { deviceKindAr, jobStatusAr } from "@/lib/labels";

const SECONDARY_CLASS =
  "min-h-11 rounded-full border border-ink/30 px-4 text-sm hover:bg-ink hover:text-sand disabled:opacity-50";

function timeAr(value: string): string {
  return new Date(value).toLocaleString("ar-SA", { dateStyle: "medium", timeStyle: "short" });
}

export function DeviceCard({
  device,
  placeAr,
  canManage,
  onEdit,
  onDeleted,
  onCaptured,
}: {
  device: Device;
  placeAr: string;
  canManage: boolean;
  onEdit: () => void;
  onDeleted: () => void;
  onCaptured: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [history, setHistory] = useState<IngestJob[] | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const captures = Boolean(device.snapshot_url || device.rtsp_url);

  async function capture() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const job = await captureNow(device.id);
      if (job.status === "failed") setError(job.error_ar ?? "تعذر الالتقاط.");
      else setMessage("التقطنا صورة وبدأ تحليلها. يظهر المخطط في قائمة المخططات حين يكتمل.");
      onCaptured();
      if (historyOpen) setHistory(await deviceHistory(device.id));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "تعذر الالتقاط. أعد المحاولة.");
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    setBusy(true);
    setError(null);
    try {
      await deleteDevice(device.id);
      onDeleted();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "تعذر حذف الجهاز.");
      setBusy(false);
    }
  }

  async function toggleHistory() {
    const opening = !historyOpen;
    setHistoryOpen(opening);
    if (!opening) return;
    try {
      setHistory(await deviceHistory(device.id));
    } catch {
      setError("تعذر تحميل سجل الجهاز.");
    }
  }

  return (
    <article className="flex h-full flex-col overflow-hidden rounded-xl bg-white/75">
      <div className="relative aspect-[16/9] bg-mud/20">
        {device.thumbnail_url ? (
          <img src={device.thumbnail_url} alt={`آخر لقطة من ${device.name_ar}`} className="h-full w-full object-cover" />
        ) : (
          <p className="flex h-full items-center justify-center p-4 text-center text-sm text-mud">لا لقطة بعد</p>
        )}
        {!device.active && (
          <span className="absolute start-2 top-2 rounded-full bg-sand px-2.5 py-0.5 text-xs font-bold text-ink">
            موقوف
          </span>
        )}
      </div>
      <div className="flex flex-1 flex-col gap-2 p-3">
        <h2 className="font-bold leading-snug">{device.name_ar}</h2>
        <p className="text-sm text-mud">
          {deviceKindAr[device.kind]} · {placeAr}
        </p>
        {device.last_capture_at && (
          <p className="text-sm">
            آخر التقاط {timeAr(device.last_capture_at)} ·{" "}
            <span className={device.last_status === "failed" ? "font-bold text-urgent" : "text-ink"}>
              {device.last_status === "failed" ? "تعذر" : "نجح"}
            </span>
          </p>
        )}
        {device.last_status === "failed" && device.last_error_ar && (
          <p className="text-sm text-urgent">{device.last_error_ar}</p>
        )}
        {device.secret_env && !device.secret_configured && (
          <p className="text-sm text-mud">
            المتغير <bdi dir="ltr">{device.secret_env}</bdi> غير مضبوط على الخادم.
          </p>
        )}
        {message && (
          <p role="status" className="text-sm text-ink">
            {message}
          </p>
        )}
        {error && (
          <p role="alert" className="text-sm text-urgent">
            {error}
          </p>
        )}

        <div className="mt-auto flex flex-wrap gap-2 pt-2">
          {canManage && captures && (
            <button
              type="button"
              onClick={capture}
              disabled={busy}
              className="min-h-11 rounded-full bg-sadu px-4 text-sm font-bold text-sand hover:bg-ink disabled:opacity-50"
            >
              {busy ? "نلتقط…" : "التقط الآن"}
            </button>
          )}
          <button type="button" onClick={toggleHistory} aria-expanded={historyOpen} className={SECONDARY_CLASS}>
            {historyOpen ? "أخفِ السجل" : "اعرض السجل"}
          </button>
          {canManage && (
            <button type="button" onClick={onEdit} disabled={busy} className={SECONDARY_CLASS}>
              عدّل
            </button>
          )}
          {canManage && !confirmingDelete && (
            <button type="button" onClick={() => setConfirmingDelete(true)} disabled={busy} className={SECONDARY_CLASS}>
              احذف
            </button>
          )}
        </div>

        {confirmingDelete && (
          <div role="alertdialog" aria-label="تأكيد الحذف" className="flex flex-col gap-2 rounded-lg bg-urgent/10 p-3 text-sm">
            <p>يُحذف الجهاز من السجل، وتبقى المخططات التي أنشأها.</p>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={remove}
                disabled={busy}
                className="min-h-11 rounded-full bg-urgent px-4 font-bold text-sand disabled:opacity-50"
              >
                احذف الجهاز
              </button>
              <button type="button" onClick={() => setConfirmingDelete(false)} className={SECONDARY_CLASS}>
                تراجع
              </button>
            </div>
          </div>
        )}

        {historyOpen && <DeviceHistory jobs={history} />}
      </div>
    </article>
  );
}

function DeviceHistory({ jobs }: { jobs: IngestJob[] | null }) {
  if (jobs === null) return <p className="text-sm text-mud">نحمّل السجل…</p>;
  if (jobs.length === 0) return <p className="text-sm text-mud">لا نشاط بعد.</p>;
  return (
    <ol className="flex flex-col divide-y divide-clay/30 text-sm">
      {jobs.map((job) => (
        <li key={job.id} className="flex flex-wrap items-center justify-between gap-2 py-1.5">
          <span>
            {timeAr(job.created_at)} · {jobStatusAr[job.status]}
          </span>
          {job.map_id ? (
            <Link href={`/dashboard/maps/${job.map_id}`} className="font-bold text-sadu underline underline-offset-4">
              المخطط
            </Link>
          ) : (
            job.error_ar && <span className="text-urgent">{job.error_ar}</span>
          )}
        </li>
      ))}
    </ol>
  );
}
