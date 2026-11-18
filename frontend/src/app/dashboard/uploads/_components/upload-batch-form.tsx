"use client";

import { ImageUpIcon, TriangleAlertIcon } from "lucide-react";
import { type DragEvent, type FormEvent, useCallback, useEffect, useState } from "react";
import { PageSkeleton, RetryAlert } from "@/app/_components/page-status";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";
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
import { cn } from "@/lib/utils";
import { BatchProgress } from "./batch-progress";

const AUTO = "auto";

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
      <p role="alert" className="mt-6 rounded-sm border border-line bg-white p-3">
        رفع الصور متاح للمساحين والمختصين.
      </p>
    );
  }

  if (batch) {
    return (
      <div className="flex flex-col gap-6">
        <header className="flex flex-wrap items-end justify-between gap-4">
          <h1 className="text-3xl font-bold">تحليل الصور المرفوعة</h1>
          <Button type="button" variant="outline" onClick={() => setBatch(null)}>
            ارفع دفعة أخرى
          </Button>
        </header>
        <BatchProgress initial={batch} sites={sites} />
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="text-3xl font-bold">ارفع صور الجدران</h1>
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
            <Label htmlFor="upload-placement" className="font-bold text-ink">
              الجدار
            </Label>
            <NativeSelect
              id="upload-placement"
              value={choice}
              onChange={(e) => setChoice(e.target.value)}
              aria-describedby="upload-placement-hint"
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
            </NativeSelect>
            <p id="upload-placement-hint" className="text-xs leading-relaxed text-mud">
              نقرأ إحداثيات الصورة قبل حذفها ونختار أقرب واجهة ضمن ٦٠ مترًا من الموقع. الصور بلا إحداثيات تنتظر أن تحدد
              واجهتها.
            </p>
          </div>

          {sources.length > 0 && (
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="upload-source" className="font-bold text-ink">
                مصدر الصور
              </Label>
              <NativeSelect id="upload-source" value={deviceId} onChange={(e) => setDeviceId(e.target.value)}>
                <option value="">رفع جماعي من الحاسوب</option>
                {sources.map((device) => (
                  <option key={device.id} value={device.id}>
                    {device.name_ar} ({deviceKindAr[device.kind]})
                  </option>
                ))}
              </NativeSelect>
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
            className={cn(
              "flex min-h-40 cursor-pointer flex-col items-start justify-center gap-1 rounded-sm border border-dashed p-5 transition-colors duration-150 has-[:focus-visible]:outline-[3px] has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-sadu",
              dropping ? "border-sadu bg-white" : "border-mud hover:border-ink hover:bg-white",
            )}
          >
            <ImageUpIcon className="mb-1 size-6 text-mud" aria-hidden="true" />
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
            <section aria-labelledby="chosen-photos" className="flex flex-col gap-1 border-t border-line pt-3">
              <h2 id="chosen-photos" className="font-bold">
                جاهز للرفع: {countAr(files.length, photoForms)}
              </h2>
              <ul className="flex flex-col divide-y divide-line">
                {files.map((file, index) => (
                  <li key={`${file.name}-${index}`} className="flex items-center justify-between gap-3">
                    <bdi className="min-w-0 truncate text-sm">{file.name}</bdi>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => setFiles((current) => current.filter((_, i) => i !== index))}
                      aria-label={`أزل ${file.name}`}
                      className="font-normal text-mud hover:text-ink"
                    >
                      أزل
                    </Button>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {error && (
            <p
              role="alert"
              className="flex items-start gap-2 rounded-sm border border-urgent/40 bg-urgent/5 p-3 text-sm leading-relaxed"
            >
              <TriangleAlertIcon className="mt-1 size-4 shrink-0 text-urgent" aria-hidden="true" />
              {error}
            </p>
          )}

          <Button type="submit" size="lg" disabled={pending || files.length === 0} className="self-start">
            {pending ? "نرفع الصور…" : "ارفع الصور وحلّلها"}
          </Button>
        </div>
      </fieldset>
    </form>
  );
}
