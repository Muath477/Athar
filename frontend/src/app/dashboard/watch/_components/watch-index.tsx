"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ApiError } from "@/lib/api";
import { useMe } from "@/lib/use-me";
import {
  LEVEL_ORDER,
  type SiteRisk,
  type WatchOverview,
  areaAr,
  copernicusCredit,
  getOverview,
  levelAr,
  levelClass,
  scanSite,
  statusAr,
  strongestSignal,
  threatAr,
  zoneAr,
} from "@/lib/watch";
import { RegionMap } from "./region-map";

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

  if (!me || overview === null) {
    return error ? <p role="alert" className="pt-6">{error}</p> : <IndexSkeleton />;
  }

  const counts = LEVEL_ORDER.map((level) => ({
    level,
    count: overview.sites.filter((s) => (s.latest?.level ?? "unknown") === level).length,
  })).filter((c) => c.count > 0);
  const latest = overview.sites.find((s) => s.latest)?.latest ?? null;

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-2">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-3xl font-bold leading-tight">رصد محيط المواقع من الفضاء</h1>
          {overview.is_sample && (
            <span className="rounded-full border-2 border-dashed border-sadu px-3 py-0.5 text-sm font-bold text-sadu">
              بيانات تجريبية للعرض
            </span>
          )}
        </div>
        <p className="max-w-3xl text-mud">
          نقارن صور Sentinel-2 للشهر الأخير بصور السنة التي قبله، داخل حدود كل موقع وفي محيط ١٥٠ م حوله. أي تغيّر هنا
          تنبيه يحتاج زيارة، لا حكم على حالة الجدران.
        </p>
        {counts.length > 0 && (
          <ul className="flex flex-wrap gap-2 pt-1" aria-label="ملخص درجات الخطر">
            {counts.map(({ level, count }) => (
              <li key={level} className={`rounded-full px-3 py-1 text-sm ${levelClass[level]}`}>
                {levelAr[level]} <strong className="tabular-nums">{count.toLocaleString("ar-SA")}</strong>
              </li>
            ))}
          </ul>
        )}
      </header>

      {error && (
        <p role="alert" className="rounded-lg bg-urgent/10 px-4 py-2 text-urgent">
          {error}
        </p>
      )}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
        <RegionMap sites={overview.sites} />
        <ol className="flex flex-col gap-2" aria-label="المواقع مرتبة حسب الأولوية">
          {overview.sites.map((site, index) => (
            <SiteRow
              key={site.site_id}
              rank={index + 1}
              site={site}
              busy={scanning === site.site_id}
              disabled={scanning !== null}
              onScan={() => scan(site.site_id)}
            />
          ))}
        </ol>
      </div>

      <p className="text-xs text-mud">{copernicusCredit(latest)}</p>
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
  onScan: () => void;
}) {
  const scan = site.latest;
  const level = scan?.level ?? "unknown";
  const strongest = strongestSignal(scan);

  return (
    <li className="flex flex-wrap items-center gap-x-4 gap-y-2 rounded-xl bg-white/75 p-3">
      <span className="w-6 text-center text-sm tabular-nums text-mud">{rank.toLocaleString("ar-SA")}</span>
      <div className="flex min-w-0 flex-1 flex-col gap-0.5">
        <Link href={`/dashboard/watch/${site.site_id}`} className="font-bold leading-snug hover:text-sadu">
          {site.name_ar}
        </Link>
        <p className="text-sm text-mud">
          {scan === null && "لم يُفحص بعد"}
          {scan !== null && scan.status !== "ok" && statusAr[scan.status]}
          {scan?.status === "ok" && strongest === null && "لا تغيّر ملحوظ"}
          {strongest && (
            <>
              {threatAr[strongest.threat]} {zoneAr[strongest.zone]} · {areaAr(strongest.area_m2)}
            </>
          )}
        </p>
      </div>
      <span className={`rounded-full px-3 py-0.5 text-sm font-bold ${levelClass[level]}`}>{levelAr[level]}</span>
      <button
        type="button"
        onClick={onScan}
        disabled={disabled}
        aria-busy={busy}
        className="rounded-full border border-ink/30 px-4 py-1.5 text-sm transition-colors hover:bg-ink hover:text-sand disabled:opacity-50"
      >
        {busy ? "يُفحص…" : "افحص الآن"}
      </button>
    </li>
  );
}

function IndexSkeleton() {
  return (
    <div className="flex animate-pulse flex-col gap-6 motion-reduce:animate-none" aria-busy="true">
      <div className="h-9 w-80 rounded bg-clay/25" />
      <div className="grid gap-6 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
        <div className="aspect-[16/9] rounded-xl bg-clay/20" />
        <div className="flex flex-col gap-2">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="h-16 rounded-xl bg-clay/20" />
          ))}
        </div>
      </div>
    </div>
  );
}
