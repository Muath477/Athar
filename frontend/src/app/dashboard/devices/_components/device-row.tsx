"use client";

import { CameraIcon, TriangleAlertIcon } from "lucide-react";
import Link from "next/link";
import { type MouseEvent, useId, useState } from "react";
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
import { ApiError, type Site } from "@/lib/api";
import { type Device, type IngestJob, captureNow, deleteDevice, deviceHistory } from "@/lib/ingest";
import { deviceKindAr, jobStatusAr } from "@/lib/labels";
import { DeviceSheet } from "./device-form";

function timeAr(value: string): string {
  return new Date(value).toLocaleString("ar-SA", { dateStyle: "medium", timeStyle: "short" });
}

export function DeviceRow({
  device,
  placeAr,
  sites,
  canManage,
  onChanged,
}: {
  device: Device;
  placeAr: string;
  sites: Site[];
  canManage: boolean;
  onChanged: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [history, setHistory] = useState<IngestJob[] | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const rowId = useId();
  const historyId = `${rowId}-history`;
  const nameId = `${rowId}-name`;
  const captures = Boolean(device.snapshot_url || device.rtsp_url);
  const failed = device.last_status === "failed";

  async function capture() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const job = await captureNow(device.id);
      if (job.status === "failed") setError(job.error_ar ?? "تعذر الالتقاط.");
      else setMessage("التقطنا صورة وبدأ تحليلها. يظهر المخطط في قائمة المخططات حين يكتمل.");
      onChanged();
      if (historyOpen) setHistory(await deviceHistory(device.id));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "تعذر الالتقاط. أعد المحاولة.");
    } finally {
      setBusy(false);
    }
  }

  async function remove(event: MouseEvent<HTMLButtonElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await deleteDevice(device.id);
      setConfirmingDelete(false);
      onChanged();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "تعذر حذف الجهاز.");
      setConfirmingDelete(false);
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
    <article aria-labelledby={nameId} className="flex flex-col gap-3 p-3 sm:flex-row sm:items-start">
      <div className="aspect-video w-full shrink-0 overflow-hidden rounded-sm bg-clay/60 sm:w-40">
        {device.thumbnail_url ? (
          <img src={device.thumbnail_url} alt={`آخر لقطة من ${device.name_ar}`} className="size-full object-cover" />
        ) : (
          <p className="flex size-full items-center justify-center p-2 text-center text-sm text-ink">لا لقطة بعد</p>
        )}
      </div>

      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <div className="flex flex-wrap items-center gap-2">
          <h2 id={nameId} className="font-bold">
            {device.name_ar}
          </h2>
          {!device.active && <Badge variant="outline">موقوف</Badge>}
        </div>
        <p className="text-sm text-mud">
          {deviceKindAr[device.kind]} · {placeAr}
        </p>
        {device.last_capture_at && (
          <p className="text-sm">
            آخر التقاط {timeAr(device.last_capture_at)} ·{" "}
            {failed ? (
              <span className="inline-flex items-center gap-1 font-bold text-urgent">
                <TriangleAlertIcon className="size-4" aria-hidden="true" />
                تعذر
              </span>
            ) : (
              "نجح"
            )}
          </p>
        )}
        {failed && device.last_error_ar && <p className="text-sm text-urgent">{device.last_error_ar}</p>}
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
        {historyOpen && (
          <div id={historyId} className="mt-2 border-t border-line pt-2">
            <DeviceHistory jobs={history} />
          </div>
        )}
      </div>

      <div className="flex flex-wrap gap-1 sm:max-w-64 sm:justify-end">
        {canManage && captures && (
          <Button type="button" variant="outline" size="sm" onClick={capture} disabled={busy}>
            <CameraIcon aria-hidden="true" />
            {busy ? "نلتقط…" : "التقط الآن"}
          </Button>
        )}
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={toggleHistory}
          aria-expanded={historyOpen}
          aria-controls={historyOpen ? historyId : undefined}
        >
          {historyOpen ? "أخفِ السجل" : "اعرض السجل"}
        </Button>
        {canManage && (
          <DeviceSheet
            device={device}
            sites={sites}
            onSaved={onChanged}
            trigger={
              <Button type="button" variant="ghost" size="sm" disabled={busy}>
                عدّل
              </Button>
            }
          />
        )}
        {canManage && (
          <AlertDialog open={confirmingDelete} onOpenChange={setConfirmingDelete}>
            <AlertDialogTrigger asChild>
              <Button type="button" variant="ghost" size="sm" disabled={busy} className="text-urgent">
                احذف
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>احذف {device.name_ar}؟</AlertDialogTitle>
                <AlertDialogDescription>يُحذف الجهاز من السجل، وتبقى المخططات التي أنشأها.</AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogAction variant="destructive" disabled={busy} onClick={remove}>
                  احذف الجهاز
                </AlertDialogAction>
                <AlertDialogCancel>تراجع</AlertDialogCancel>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        )}
      </div>
    </article>
  );
}

function DeviceHistory({ jobs }: { jobs: IngestJob[] | null }) {
  if (jobs === null) return <p className="text-sm text-mud">نحمّل السجل…</p>;
  if (jobs.length === 0) return <p className="text-sm text-mud">لا نشاط بعد.</p>;
  return (
    <ol className="flex flex-col divide-y divide-line text-sm">
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
