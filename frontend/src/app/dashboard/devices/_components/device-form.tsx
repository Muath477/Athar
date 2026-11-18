"use client";

import { type FormEvent, useState } from "react";
import { ApiError, type Site } from "@/lib/api";
import { type Device, type DeviceInput, type DeviceKind, createDevice, updateDevice } from "@/lib/ingest";
import { deviceKindAr } from "@/lib/labels";

const INPUT_CLASS = "min-h-11 rounded-lg border border-mud/60 bg-white px-3 text-base";
const KINDS: DeviceKind[] = ["fixed_camera", "drone", "phone", "upload"];

function textOrNull(form: FormData, field: string): string | null {
  const value = String(form.get(field) ?? "").trim();
  return value || null;
}

export function DeviceForm({
  device,
  sites,
  onSaved,
  onCancel,
}: {
  device: Device | null;
  sites: Site[];
  onSaved: (device: Device) => void;
  onCancel: () => void;
}) {
  const [kind, setKind] = useState<DeviceKind>(device?.kind ?? "fixed_camera");
  const [siteId, setSiteId] = useState(device?.site_id ?? sites[0]?.id ?? "");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const camera = kind === "fixed_camera";
  const facades = sites.find((s) => s.id === siteId)?.facades ?? [];

  function chooseKind(next: DeviceKind) {
    setKind(next);
    if (next === "fixed_camera" && !siteId) setSiteId(sites[0]?.id ?? "");
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const interval = textOrNull(form, "interval_h");
    const input: DeviceInput = {
      kind,
      name_ar: String(form.get("name_ar")).trim(),
      site_id: siteId || null,
      facade_id: textOrNull(form, "facade_id"),
      snapshot_url: camera ? textOrNull(form, "snapshot_url") : null,
      rtsp_url: camera ? textOrNull(form, "rtsp_url") : null,
      username: camera ? textOrNull(form, "username") : null,
      secret_env: camera ? textOrNull(form, "secret_env") : null,
      interval_h: camera && interval ? Number(interval) : null,
      active: form.get("active") === "on",
    };
    setPending(true);
    setError(null);
    try {
      onSaved(device ? await updateDevice(device.id, input) : await createDevice(input));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "تعذر حفظ الجهاز. أعد المحاولة.");
      setPending(false);
    }
  }

  return (
    <form
      onSubmit={submit}
      aria-labelledby="device-form-title"
      className="flex flex-col gap-4 rounded-xl border border-clay/50 bg-white/80 p-4"
    >
      <h2 id="device-form-title" className="text-xl font-bold">
        {device ? `عدّل ${device.name_ar}` : "أضف جهازًا"}
      </h2>
      <fieldset disabled={pending} className="grid gap-4 sm:grid-cols-2">
        <label className="flex flex-col gap-1">
          <span>نوع الجهاز</span>
          <select value={kind} onChange={(e) => chooseKind(e.target.value as DeviceKind)} className={INPUT_CLASS}>
            {KINDS.map((k) => (
              <option key={k} value={k}>
                {deviceKindAr[k]}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span>الاسم</span>
          <input name="name_ar" required maxLength={200} defaultValue={device?.name_ar} className={INPUT_CLASS} />
        </label>
        <label className="flex flex-col gap-1">
          <span>الموقع</span>
          <select
            value={siteId}
            required={camera}
            onChange={(e) => setSiteId(e.target.value)}
            className={INPUT_CLASS}
          >
            {!camera && <option value="">بلا موقع محدد</option>}
            {sites.map((site) => (
              <option key={site.id} value={site.id}>
                {site.name_ar}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span>الواجهة التي تصوّرها</span>
          <select
            key={siteId}
            name="facade_id"
            defaultValue={device?.site_id === siteId ? (device?.facade_id ?? "") : ""}
            className={INPUT_CLASS}
          >
            <option value="">حدّد من إحداثيات الصورة أو لاحقًا</option>
            {facades.map((facade) => (
              <option key={facade.id} value={facade.id}>
                {facade.name_ar}
              </option>
            ))}
          </select>
        </label>

        {camera && (
          <>
            <label className="flex flex-col gap-1 sm:col-span-2">
              <span>رابط اللقطة (HTTP أو HTTPS)</span>
              <input
                name="snapshot_url"
                type="url"
                dir="ltr"
                maxLength={500}
                defaultValue={device?.snapshot_url ?? ""}
                placeholder="http://192.168.1.64/ISAPI/Streaming/channels/101/picture"
                aria-describedby="snapshot-hint"
                className={INPUT_CLASS}
              />
              <span id="snapshot-hint" className="text-sm text-mud">
                معظم الكاميرات ومسجلات الفيديو تعرض صورة ثابتة على رابط كهذا. العناوين الداخلية تحتاج إضافتها إلى
                <bdi> SADU_CAMERA_ALLOWED_HOSTS</bdi>.
              </span>
            </label>
            <label className="flex flex-col gap-1 sm:col-span-2">
              <span>رابط البث RTSP (اختياري)</span>
              <input
                name="rtsp_url"
                dir="ltr"
                maxLength={500}
                defaultValue={device?.rtsp_url ?? ""}
                placeholder="rtsp://192.168.1.64/Streaming/Channels/101"
                aria-describedby="rtsp-hint"
                className={INPUT_CLASS}
              />
              <span id="rtsp-hint" className="text-sm text-mud">
                يُستخدم إن لم يوجد رابط لقطة، ويحتاج ffmpeg على الخادم.
              </span>
            </label>
            <label className="flex flex-col gap-1">
              <span>اسم المستخدم للكاميرا</span>
              <input
                name="username"
                dir="ltr"
                maxLength={100}
                autoComplete="off"
                defaultValue={device?.username ?? ""}
                className={INPUT_CLASS}
              />
            </label>
            <label className="flex flex-col gap-1">
              <span>متغير البيئة لكلمة المرور</span>
              <input
                name="secret_env"
                dir="ltr"
                maxLength={100}
                pattern="SADU_CAMERA_SECRET_[A-Z0-9_]+"
                autoComplete="off"
                defaultValue={device?.secret_env ?? ""}
                placeholder="SADU_CAMERA_SECRET_GATE"
                aria-describedby="secret-hint"
                className={INPUT_CLASS}
              />
              <span id="secret-hint" className="text-sm text-mud">
                لا يحفظ أثر كلمة المرور؛ يقرؤها الخادم من هذا المتغير عند الالتقاط.
              </span>
            </label>
            <label className="flex flex-col gap-1">
              <span>الالتقاط كل (ساعة)</span>
              <input
                name="interval_h"
                type="number"
                inputMode="numeric"
                min={1}
                max={720}
                defaultValue={device?.interval_h ?? ""}
                placeholder="الافتراضي ٢٤"
                className={INPUT_CLASS}
              />
            </label>
          </>
        )}

        <label className="flex min-h-11 items-center gap-2 self-end">
          <input name="active" type="checkbox" defaultChecked={device?.active ?? true} className="h-5 w-5" />
          <span>مفعّل</span>
        </label>
      </fieldset>

      {error && (
        <p role="alert" className="rounded-xl border border-urgent/40 bg-urgent/10 p-3 text-sm">
          {error}
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        <button
          type="submit"
          disabled={pending}
          className="min-h-11 rounded-full bg-sadu px-6 font-bold text-sand hover:bg-ink disabled:opacity-50"
        >
          {pending ? "نحفظ…" : "احفظ الجهاز"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="min-h-11 rounded-full border border-ink/30 px-4 hover:bg-ink hover:text-sand"
        >
          ألغِ
        </button>
      </div>
    </form>
  );
}
