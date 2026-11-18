"use client";

import { TriangleAlertIcon } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { ApiError, can } from "@/lib/api";
import { alerts, countAr } from "@/lib/plural";
import { useMe } from "@/lib/use-me";
import {
  LEVEL_ORDER,
  type SiteRisk,
  type WatchOverview,
  areaAr,
  getOverview,
  levelAr,
  scanSite,
  statusAr,
  strongestSignal,
  threatAr,
  trendAr,
  warningAr,
  zoneAr,
} from "@/lib/watch";
import { LevelBadge, SampleBadge } from "./level-badge";
import { RegionMap } from "./region-map";
import { CopernicusCredit, IndexSkeleton, LoadError } from "./watch-states";

export function WatchIndex() {
  const me = useMe();
  const [overview, setOverview] = useState<WatchOverview | null>(null);
  const [scanning, setScanning] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    () =>
      getOverview().then(setOverview, (e) =>
        setError(e instanceof ApiError ? e.message : "تعذر تحميل رصد المواقع."),
      ),
    [],
  );

  useEffect(() => {
    if (me) load();
  }, [me, load]);

  async function scan(siteId: string) {
    setScanning(siteId);
    setError(null);
    try {
      await scanSite(siteId);
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "تعذر فحص الموقع الآن.");
    } finally {
      setScanning(null);
    }
  }

  function retry() {
    setError(null);
    load();
  }

  if (!me || overview === null) {
    return error ? <LoadError message={error} onRetry={retry} /> : <IndexSkeleton />;
  }

  const counts = LEVEL_ORDER.map((level) => ({
    level,
    count: overview.sites.filter((s) => (s.latest?.level ?? "unknown") === level).length,
  })).filter((c) => c.count > 0);
  const latest = overview.sites.find((s) => s.latest)?.latest ?? null;
  const alertSites = overview.sites.filter((s) => s.alert && s.latest && !s.latest.acknowledged_at);

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-2">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-3xl font-bold">رصد محيط المواقع من الفضاء</h1>
          {overview.is_sample && <SampleBadge>بيانات تجريبية للعرض</SampleBadge>}
        </div>
        <p className="max-w-3xl text-mud">
          نقارن صور <bdi dir="ltr">Sentinel-2</bdi> للشهر الأخير بصور السنة التي قبله، داخل حدود كل موقع وفي محيط{" "}
          <span className="whitespace-nowrap">١٥٠{"\u00a0"}م</span> حوله. أي تغيّر هنا تنبيه يحتاج زيارة، لا حكم على حالة
          الجدران.
        </p>
        {counts.length > 0 && (
          <ul className="flex flex-wrap gap-2 pt-1" aria-label="ملخص درجات الخطر">
            {counts.map(({ level, count }) => (
              <li key={level}>
                <LevelBadge level={level}>
                  {levelAr[level]} <span className="tabular-nums">{count.toLocaleString("ar-SA")}</span>
                </LevelBadge>
              </li>
            ))}
          </ul>
        )}
      </header>

      {overview.alerts_pending > 0 && (
        <div role="status" className="flex flex-col gap-1 rounded-sm border border-urgent/40 bg-urgent/5 p-3">
          <p>
            <TriangleAlertIcon className="me-1 inline size-4 align-[-0.125em] text-urgent" aria-hidden="true" />
            <strong>{countAr(overview.alerts_pending, alerts)}</strong> بانتظار مراجعة المختص. التنبيه يصدر عند تغيّر
            عاجل أو تغيّر يتكرر في فحصين متتاليين.
          </p>
          {alertSites.length > 0 && (
            <ul className="flex flex-wrap gap-x-6">
              {alertSites.map((site) => (
                <li key={site.site_id} className="flex min-h-11 items-center gap-2">
                  <span id={`alert-${site.site_id}`} className="font-bold">
                    {site.name_ar}
                  </span>
                  <Link
                    href={`/dashboard/watch/${site.site_id}`}
                    aria-describedby={`alert-${site.site_id}`}
                    className="inline-flex min-h-11 items-center font-bold text-sadu underline underline-offset-4"
                  >
                    راجعه الآن
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {error && (
        <p role="alert" className="rounded-sm border border-urgent/40 bg-urgent/5 p-3 text-sm">
          {error}
        </p>
      )}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
        <RegionMap sites={overview.sites} />
        <ol
          className="order-first flex flex-col self-start divide-y divide-line rounded-sm border border-line bg-white lg:order-none"
          aria-label="المواقع مرتبة حسب الأولوية"
        >
          {overview.sites.map((site, index) => (
            <SiteRow
              key={site.site_id}
              rank={index + 1}
              site={site}
              busy={scanning === site.site_id || site.scanning}
              disabled={scanning !== null || site.scanning}
              onScan={can(me, "survey") ? () => scan(site.site_id) : null}
            />
          ))}
        </ol>
      </div>

      <CopernicusCredit scan={latest} />
    </div>
  );
}

function SiteRow({
  rank,
  site,
  busy,
  disabled,
  onScan,
}: {
  rank: number;
  site: SiteRisk;
  busy: boolean;
  disabled: boolean;
  onScan: (() => void) | null;
}) {
  const scan = site.latest;
  const level = scan?.level ?? "unknown";
  const strongest = strongestSignal(scan);
  const prominent = level === "urgent" || level === "moderate" || level === "watch";

  return (
    <li className="flex flex-wrap items-center gap-x-4 gap-y-2 p-3">
      <span className="w-6 text-center text-sm tabular-nums text-mud">{rank.toLocaleString("ar-SA")}</span>
      <div className="flex min-w-0 flex-1 flex-col gap-0.5">
        <Link href={`/dashboard/watch/${site.site_id}`} className="font-bold leading-snug hover:text-sadu">
          {site.name_ar}
        </Link>
        <p className="text-sm text-mud">
          {scan === null && (site.failed_attempt ? statusAr[site.failed_attempt.status] : "لم يُفحص بعد")}
          {scan !== null && strongest === null && "لا تغيّر ملحوظ"}
          {strongest && (
            <>
              {threatAr[strongest.threat]} {zoneAr[strongest.zone]} ·{" "}
              <bdi className="whitespace-nowrap">{areaAr(strongest.area_m2)}</bdi>
            </>
          )}
          {warningAr(site) && (
            <span className="block text-xs">
              {site.alert && (
                <strong className="text-urgent">
                  <TriangleAlertIcon className="me-0.5 inline size-3.5 align-[-0.125em]" aria-hidden="true" />
                  تنبيه ·{" "}
                </strong>
              )}
              {warningAr(site)}
              {site.trend && site.trend !== "new" && <> · {trendAr[site.trend]}</>}
            </span>
          )}
          {scan !== null && site.failed_attempt && (
            <span className="block text-xs">آخر محاولة: {statusAr[site.failed_attempt.status]}</span>
          )}
        </p>
      </div>
      <div className="flex basis-full items-center justify-end gap-3 sm:basis-auto">
        <LevelBadge level={level} />
        {onScan && (
          <Button
            type="button"
            variant={prominent ? "outline" : "ghost"}
            size="sm"
            onClick={onScan}
            disabled={disabled}
            aria-busy={busy}
            aria-label={busy ? `يُفحص ${site.name_ar}` : prominent ? `افحص ${site.name_ar} الآن` : `افحص ${site.name_ar}`}
            className={prominent ? undefined : "text-mud hover:text-ink"}
          >
            {busy ? "يُفحص…" : prominent ? "افحص الآن" : "افحص"}
          </Button>
        )}
      </div>
    </li>
  );
}
