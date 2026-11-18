"use client";

import { type DragEvent, type FormEvent, useCallback, useEffect, useState } from "react";
import { PageSkeleton, RetryAlert } from "@/app/_components/page-status";
import { ApiError, type Site, can, request } from "@/lib/api";
import {
  type Device,
  PHOTO_ACCEPT,
  type PhotoCheck,
  type UploadBatch,
  type UploadPlacement,
  checkPhotos,
  listDevices,
  uploadPhotos,
} from "@/lib/ingest";
import { deviceKindAr } from "@/lib/labels";
import { countAr, photos as photoForms } from "@/lib/plural";
import { useMeState } from "@/lib/use-me";
import { BatchProgress } from "./batch-progress";

const AUTO = "auto";
const SELECT_CLASS = "min-h-11 rounded-lg border border-mud/60 bg-white px-3 text-base";

function placementFor(choice: string, deviceId: string): UploadPlacement {
  const [kind, id] = choice.split(":");
  const placement: UploadPlacement = deviceId ? { device_id: deviceId } : {};
  if (kind === "site") placement.site_id = id;
  if (kind === "facade") placement.facade_id = id;
  return placement;
}

export function UploadBatchForm() {
  const { me, error: meError, retry: retryMe } = useMeState();
  const [sites, setSites] = useState<Site[]>([]);
  const [sources, setSources] = useState<Device[]>([]);
  const [choice, setChoice] = useState(AUTO);
  const [deviceId, setDeviceId] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [rejected, setRejected] = useState<PhotoCheck["rejected"]>([]);
  const [dropping, setDropping] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [batch, setBatch] = useState<UploadBatch | null>(null);

  const load = useCallback(() => {
    Promise.all([request<Site[]>("/sites"), listDevices()]).then(
      ([loadedSites, devices]) => {
        setSites(loadedSites);
        setSources(devices.filter((d) => d.kind !== "fixed_camera"));
      },
      (e) => setLoadError(e instanceof ApiError ? e.message : "تعذر تحميل المواقع والأجهزة."),
    );
  }, []);

  useEffect(() => {
    if (me) load();
  }, [me, load]);

  function addFiles(list: FileList | null) {
    const check = checkPhotos(Array.from(list ?? []), files.length);
    setFiles((current) => [...current, ...check.accepted]);
    setRejected(check.rejected);
    setError(null);
  }

  function onDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setDropping(false);
    addFiles(event.dataTransfer.files);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (files.length === 0) return;
    setPending(true);
    setError(null);
    try {
      setBatch(await uploadPhotos(files, placementFor(choice, deviceId)));
      setFiles([]);
      setRejected([]);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "تعذر رفع الصور. تحقق من الاتصال وأعد المحاولة.");
    } finally {
      setPending(false);
    }
  }

  if (meError) {
    return (
      <div className="pt-6">
        <RetryAlert message={meError} onRetry={retryMe} />
      </div>
    );
  }
  if (!me) return <PageSkeleton />;

  if (!can(me, "survey")) {
    return (
      <p role="alert" className="pt-6 text-mud">
        رفع الصور متاح للمساحين والمختصين.
      </p>
    );
  }

  if (batch) {
    return (
      <div className="flex flex-col gap-6">
        <header className="flex flex-wrap items-end justify-between gap-4">
          <h1 className="text-3xl font-bold leading-snug">تحليل الصور المرفوعة</h1>
          <button
            type="button"
            onClick={() => setBatch(null)}
            className="min-h-11 rounded-full border border-ink/30 px-4 hover:bg-ink hover:text-sand"
          >
            ارفع دفعة أخرى
          </button>
        </header>
        <BatchProgress initial={batch} sites={sites} />
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="text-3xl font-bold leading-snug">ارفع صور الجدران</h1>
        <p className="max-w-prose text-mud">
          ارفع حتى ٣٠ صورة من جوالك أو من الطائرة المسيّرة أو من أرشيف الموقع. نطمس الوجوه ونحذف بيانات الصورة، ثم يرسم
          أثر لكل صورة مخطط تلف ينتظر اعتماد المختص.
        </p>
      </header>

      {loadError && (
        <RetryAlert
          message={loadError}
          onRetry={() => {
            setLoadError(null);
            load();
          }}
        />
      )}

      <fieldset disabled={pending} className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="upload-placement" className="font-bold">
              الجدار
            </label>
            <select
              id="upload-placement"
              value={choice}
              onChange={(e) => setChoice(e.target.value)}
              aria-describedby="upload-placement-hint"
              className={SELECT_CLASS}
            >
              <option value={AUTO}>حدّد تلقائيًا من الموقع الجغرافي</option>
              {sites.map((site) => (
                <optgroup key={site.id} label={site.name_ar}>
                  <option value={`site:${site.id}`}>أي واجهة في {site.name_ar} حسب الموقع الجغرافي</option>
                  {site.facades.map((facade) => (
                    <option key={facade.id} value={`facade:${facade.id}`}>
                      {facade.name_ar}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
            <p id="upload-placement-hint" className="text-sm text-mud">
              نقرأ إحداثيات الصورة قبل حذفها ونختار أقرب واجهة ضمن ٦٠ مترًا من الموقع. الصور بلا إحداثيات تنتظر أن تحدد
              واجهتها.
            </p>
          </div>

          {sources.length > 0 && (
            <div className="flex flex-col gap-1.5">
              <label htmlFor="upload-source" className="font-bold">
                مصدر الصور
              </label>
              <select
                id="upload-source"
                value={deviceId}
                onChange={(e) => setDeviceId(e.target.value)}
                className={SELECT_CLASS}
              >
                <option value="">رفع جماعي من الحاسوب</option>
                {sources.map((device) => (
                  <option key={device.id} value={device.id}>
                    {device.name_ar} ({deviceKindAr[device.kind]})
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        <div className="flex flex-col gap-3">
          <label
            onDragOver={(e) => {
              e.preventDefault();
              setDropping(true);
            }}
            onDragLeave={() => setDropping(false)}
            onDrop={onDrop}
            className={`flex min-h-40 cursor-pointer flex-col justify-center gap-1 rounded-xl border-2 border-dashed p-4 transition-colors has-[:focus-visible]:outline has-[:focus-visible]:outline-[3px] has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-sadu ${
              dropping ? "border-sadu bg-white/60" : "border-mud hover:bg-white/60"
            }`}
          >
            <span className="font-bold">اختر الصور أو اسحبها هنا</span>
            <span className="text-sm text-mud">JPEG أو PNG أو HEIC، حتى ٨ ميغابايت للصورة.</span>
            <input
              type="file"
              multiple
              accept={PHOTO_ACCEPT}
              aria-describedby={rejected.length > 0 ? "upload-rejected" : undefined}
              className="sr-only"
              onChange={(e) => {
                addFiles(e.target.files);
                e.target.value = "";
              }}
            />
          </label>

          {rejected.length > 0 && (
            <ul id="upload-rejected" role="alert" className="flex flex-col gap-1 text-sm text-urgent">
              {rejected.map((item) => (
                <li key={item.name}>
                  <bdi>{item.name}</bdi>: {item.reason}
                </li>
              ))}
            </ul>
          )}

          {files.length > 0 && (
            <section aria-labelledby="chosen-photos" className="flex flex-col gap-2 rounded-xl bg-white/75 p-3">
              <h2 id="chosen-photos" className="font-bold">
                جاهز للرفع: {countAr(files.length, photoForms)}
              </h2>
              <ul className="flex flex-col divide-y divide-clay/30">
                {files.map((file, index) => (
                  <li key={`${file.name}-${index}`} className="flex items-center justify-between gap-3 py-1">
                    <bdi className="min-w-0 truncate">{file.name}</bdi>
                    <button
                      type="button"
                      onClick={() => setFiles((current) => current.filter((_, i) => i !== index))}
                      aria-label={`أزل ${file.name}`}
                      className="min-h-11 shrink-0 rounded-full px-3 text-sm text-mud hover:bg-clay/20 hover:text-ink"
                    >
                      أزل
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {error && (
            <p role="alert" className="rounded-xl border border-urgent/40 bg-urgent/10 p-3 text-sm leading-relaxed">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={pending || files.length === 0}
            className="min-h-11 rounded-full bg-sadu px-6 text-lg font-bold text-sand hover:bg-ink disabled:opacity-50"
          >
            {pending ? "نرفع الصور…" : "ارفع الصور وحلّلها"}
          </button>
        </div>
      </fieldset>
    </form>
  );
}
