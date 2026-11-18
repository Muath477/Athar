"use client";

import { type FormEvent, type ReactNode, useState } from "react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";
import {
  Sheet,
  SheetClose,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { ApiError, type Site } from "@/lib/api";
import { type Device, type DeviceInput, type DeviceKind, createDevice, updateDevice } from "@/lib/ingest";
import { deviceKindAr } from "@/lib/labels";
import { cn } from "@/lib/utils";

const KINDS: DeviceKind[] = ["fixed_camera", "drone", "phone", "upload"];

function textOrNull(form: FormData, field: string): string | null {
  const value = String(form.get(field) ?? "").trim();
  return value || null;
}

export function DeviceSheet({
  device,
  sites,
  trigger,
  onSaved,
}: {
  device: Device | null;
  sites: Site[];
  trigger: ReactNode;
  onSaved: (device: Device) => void;
}) {
  const [open, setOpen] = useState(false);

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>{trigger}</SheetTrigger>
      <SheetContent className="w-full overflow-y-auto sm:max-w-lg">
        <SheetHeader>
          <SheetTitle>{device ? `عدّل ${device.name_ar}` : "أضف جهازًا"}</SheetTitle>
          <SheetDescription>
            الكاميرا الثابتة تلتقط صورة دورية للواجهة، والطائرة والمحطة تُنسب إليهما الصور المرفوعة.
          </SheetDescription>
        </SheetHeader>
        <DeviceForm
          device={device}
          sites={sites}
          onSaved={(saved) => {
            setOpen(false);
            onSaved(saved);
          }}
        />
      </SheetContent>
    </Sheet>
  );
}

function DeviceForm({
  device,
  sites,
  onSaved,
}: {
  device: Device | null;
  sites: Site[];
  onSaved: (device: Device) => void;
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
      aria-label={device ? `عدّل ${device.name_ar}` : "أضف جهازًا"}
      className="flex flex-1 flex-col"
    >
      <fieldset disabled={pending} className="grid gap-4 px-4 sm:grid-cols-2">
        <Field id="device-kind" label="نوع الجهاز">
          <NativeSelect id="device-kind" value={kind} onChange={(e) => chooseKind(e.target.value as DeviceKind)}>
            {KINDS.map((k) => (
              <option key={k} value={k}>
                {deviceKindAr[k]}
              </option>
            ))}
          </NativeSelect>
        </Field>
        <Field id="device-name" label="الاسم">
          <Input id="device-name" name="name_ar" required maxLength={200} defaultValue={device?.name_ar} />
        </Field>
        <Field id="device-site" label="الموقع">
          <NativeSelect id="device-site" value={siteId} required={camera} onChange={(e) => setSiteId(e.target.value)}>
            {!camera && <option value="">بلا موقع محدد</option>}
            {sites.map((site) => (
              <option key={site.id} value={site.id}>
                {site.name_ar}
              </option>
            ))}
          </NativeSelect>
        </Field>
        <Field id="device-facade" label="الواجهة التي تصوّرها">
          <NativeSelect
            key={siteId}
            id="device-facade"
            name="facade_id"
            defaultValue={device?.site_id === siteId ? (device?.facade_id ?? "") : ""}
          >
            <option value="">حدّد من إحداثيات الصورة أو لاحقًا</option>
            {facades.map((facade) => (
              <option key={facade.id} value={facade.id}>
                {facade.name_ar}
              </option>
            ))}
          </NativeSelect>
        </Field>

        {camera && (
          <>
            <Field
              id="device-snapshot"
              label="رابط اللقطة (HTTP أو HTTPS)"
              hint={
                <>
                  معظم الكاميرات ومسجلات الفيديو تعرض صورة ثابتة على رابط كهذا. العناوين الداخلية تحتاج إضافتها إلى
                  <bdi> SADU_CAMERA_ALLOWED_HOSTS</bdi>.
                </>
              }
              className="sm:col-span-2"
            >
              <Input
                id="device-snapshot"
                name="snapshot_url"
                type="url"
                dir="ltr"
                maxLength={500}
                defaultValue={device?.snapshot_url ?? ""}
                placeholder="http://192.168.1.64/ISAPI/Streaming/channels/101/picture"
                aria-describedby="device-snapshot-hint"
              />
            </Field>
            <Field
              id="device-rtsp"
              label="رابط البث RTSP (اختياري)"
              hint="يُستخدم إن لم يوجد رابط لقطة، ويحتاج ffmpeg على الخادم."
              className="sm:col-span-2"
            >
              <Input
                id="device-rtsp"
                name="rtsp_url"
                dir="ltr"
                maxLength={500}
                defaultValue={device?.rtsp_url ?? ""}
                placeholder="rtsp://192.168.1.64/Streaming/Channels/101"
                aria-describedby="device-rtsp-hint"
              />
            </Field>
            <Field id="device-username" label="اسم المستخدم للكاميرا">
              <Input
                id="device-username"
                name="username"
                dir="ltr"
                maxLength={100}
                autoComplete="off"
                defaultValue={device?.username ?? ""}
              />
            </Field>
            <Field
              id="device-secret"
              label="متغير البيئة لكلمة المرور"
              hint="لا يحفظ أثر كلمة المرور؛ يقرؤها الخادم من هذا المتغير عند الالتقاط."
            >
              <Input
                id="device-secret"
                name="secret_env"
                dir="ltr"
                maxLength={100}
                pattern="SADU_CAMERA_SECRET_[A-Z0-9_]+"
                autoComplete="off"
                defaultValue={device?.secret_env ?? ""}
                placeholder="SADU_CAMERA_SECRET_GATE"
                aria-describedby="device-secret-hint"
              />
            </Field>
            <Field id="device-interval" label="الالتقاط كل (ساعة)">
              <Input
                id="device-interval"
                name="interval_h"
                type="number"
                inputMode="numeric"
                min={1}
                max={720}
                defaultValue={device?.interval_h ?? ""}
                placeholder="الافتراضي ٢٤"
              />
            </Field>
          </>
        )}

        <div className="flex min-h-11 items-center gap-2 self-end">
          <Checkbox id="device-active" name="active" defaultChecked={device?.active ?? true} />
          <Label htmlFor="device-active" className="text-base text-ink">
            مفعّل
          </Label>
        </div>
      </fieldset>

      {error && (
        <p role="alert" className="mx-4 mt-4 rounded-sm border border-urgent/40 bg-urgent/5 p-3 text-sm">
          {error}
        </p>
      )}
      <SheetFooter className="flex-row flex-wrap">
        <Button type="submit" disabled={pending}>
          {pending ? "نحفظ…" : "احفظ الجهاز"}
        </Button>
        <SheetClose asChild>
          <Button type="button" variant="outline">
            ألغِ
          </Button>
        </SheetClose>
      </SheetFooter>
    </form>
  );
}

function Field({
  id,
  label,
  hint,
  className,
  children,
}: {
  id: string;
  label: string;
  hint?: ReactNode;
  className?: string;
  children: ReactNode;
}) {
  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <Label htmlFor={id}>{label}</Label>
      {children}
      {hint && (
        <p id={`${id}-hint`} className="text-xs leading-relaxed text-mud">
          {hint}
        </p>
      )}
    </div>
  );
}
