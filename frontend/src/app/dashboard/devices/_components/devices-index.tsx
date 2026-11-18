"use client";

import { TriangleAlertIcon } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { PageSkeleton, RetryAlert } from "@/app/_components/page-status";
import { Button } from "@/components/ui/button";
import { ApiError, type Site, can, request } from "@/lib/api";
import { type Device, listDevices } from "@/lib/ingest";
import { countAr, devices as deviceForms } from "@/lib/plural";
import { useMeState } from "@/lib/use-me";
import { DeviceSheet } from "./device-form";
import { DeviceRow } from "./device-row";

function placeAr(device: Device, sites: Site[]): string {
  const site = sites.find((s) => s.id === device.site_id);
  if (!site) return "بلا موقع محدد";
  const facade = site.facades.find((f) => f.id === device.facade_id);
  return facade ? `${site.name_ar}، ${facade.name_ar}` : site.name_ar;
}

export function DevicesIndex() {
  const { me, error: meError, retry: retryMe } = useMeState();
  const [devices, setDevices] = useState<Device[] | null>(null);
  const [sites, setSites] = useState<Site[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    Promise.all([listDevices(), request<Site[]>("/sites")]).then(
      ([loadedDevices, loadedSites]) => {
        setDevices(loadedDevices);
        setSites(loadedSites);
      },
      (e) => setError(e instanceof ApiError ? e.message : "تعذر تحميل الأجهزة."),
    );
  }, []);

  useEffect(() => {
    if (me) load();
  }, [me, load]);

  if (meError || error) {
    return (
      <div className="pt-6">
        <RetryAlert
          message={meError ?? error ?? ""}
          onRetry={() => {
            if (meError) retryMe();
            setError(null);
            load();
          }}
        />
      </div>
    );
  }
  if (!me || devices === null) return <PageSkeleton />;

  const canManage = can(me, "manage_devices");
  const failing = devices.filter((d) => d.last_status === "failed").length;

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h1 className="text-3xl font-bold">الكاميرات والأجهزة</h1>
          <p className="text-mud">
            <strong className="text-ink">{countAr(devices.length, deviceForms)}</strong>
            {failing > 0 && (
              <>
                {" · "}
                <strong className="inline-flex items-center gap-1 text-urgent">
                  <TriangleAlertIcon className="size-4" aria-hidden="true" />
                  تعذر آخر التقاط في {failing.toLocaleString("ar-SA")}
                </strong>
              </>
            )}
          </p>
        </div>
        {canManage && (
          <DeviceSheet device={null} sites={sites} onSaved={load} trigger={<Button type="button">أضف جهازًا</Button>} />
        )}
      </header>

      {devices.length === 0 ? (
        <section className="flex flex-col items-start gap-3 rounded-sm border border-line bg-white p-5">
          <h2 className="text-xl font-bold">لا كاميرات مسجلة بعد</h2>
          <p className="max-w-prose leading-relaxed">
            سجّل كاميرات الموقع الثابتة ليلتقط أثر صورة دورية لكل واجهة ويحللها، وسجّل الطائرات المسيّرة لتُنسب إليها
            الصور المرفوعة.
          </p>
        </section>
      ) : (
        <ul className="flex flex-col divide-y divide-line rounded-sm border border-line bg-white">
          {devices.map((device) => (
            <li key={device.id}>
              <DeviceRow
                device={device}
                placeAr={placeAr(device, sites)}
                sites={sites}
                canManage={canManage}
                onChanged={load}
              />
            </li>
          ))}
        </ul>
      )}

      <aside className="max-w-prose border-t border-line pt-4 text-sm leading-relaxed">
        <h2 className="mb-1 font-bold">صور جوال المساح</h2>
        <p>
          يصوّر المساح الجدار من{" "}
          <Link href="/dashboard/maps/new" className="font-bold text-sadu underline underline-offset-4">
            ارسم مخطط جدار
          </Link>
          ، أو يرفع عدة صور دفعة واحدة من{" "}
          <Link href="/dashboard/uploads" className="font-bold text-sadu underline underline-offset-4">
            رفع الصور
          </Link>
          . تُنسب هذه المخططات إلى المساح دون تسجيل جواله جهازًا.
        </p>
      </aside>
    </div>
  );
}
