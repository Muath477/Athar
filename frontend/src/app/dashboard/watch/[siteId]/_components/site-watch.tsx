"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { TriangleAlertIcon } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { ApiError, can } from "@/lib/api";
import { countAr, missions, scenes } from "@/lib/plural";
import { useMe } from "@/lib/use-me";
import {
  type GroundCheck,
  type Scan,
  type WatchOverview,
  acknowledgeScan,
  areaAr,
  getOverview,
  latestOk,
  listScans,
  requestGroundCheck,
  scanSite,
  statusAr,
  strongestSignal,
  threatAr,
  trendAr,
  warningAr,
  zoneAr,
} from "@/lib/watch";
import { LevelBadge, SampleBadge } from "../../_components/level-badge";
import { CopernicusCredit, LoadError, SiteWatchSkeleton } from "../../_components/watch-states";
import { CompareImages } from "./compare-images";

type Notice = { kind: "scan" } | { kind: "ack" } | { kind: "ground"; check: GroundCheck };

function dateAr(value: string): string {
  return new Date(value).toLocaleDateString("ar-SA", { day: "numeric", month: "long", year: "numeric" });
}

export function SiteWatch() {
  const { siteId } = useParams<{ siteId: string }>();
  const me = useMe();
  const [overview, setOverview] = useState<WatchOverview | null>(null);
  const [scans, setScans] = useState<Scan[] | null>(null);
  const [busy, setBusy] = useState<"scan" | "ground" | "ack" | null>(null);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [error, setError] = useState<string | null>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);

  const load = useCallback(
    () =>
      Promise.all([getOverview(), listScans(siteId)]).then(
        ([o, s]) => {
          setOverview(o);
          setScans(s);
        },
        (e) => setError(e instanceof ApiError ? e.message : "تعذر تحميل رصد الموقع."),
      ),
    [siteId],
  );

  useEffect(() => {
    if (me) load();
  }, [me, load]);

  async function run(kind: "scan" | "ground" | "ack", action: () => Promise<Notice>) {
    setBusy(kind);
    setError(null);
    setNotice(null);
    try {
      const done = await action();
      await load();
      setNotice(done);
      headingRef.current?.focus();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "تعذر تنفيذ الطلب.");
    } finally {
      setBusy(null);
    }
  }

  function retry() {
    setError(null);
    load();
  }

  const site = overview?.sites.find((s) => s.site_id === siteId);
  if (!me || !overview || scans === null) {
    return error ? <LoadError message={error} onRetry={retry} /> : <SiteWatchSkeleton />;
  }
  if (!site) return <p className="pt-6">هذا الموقع غير موجود في الرصد.</p>;

  const latest = latestOk(scans);
  const lastAttempt = scans[0] ?? null;
  const failedSince = lastAttempt && lastAttempt.status !== "ok" ? lastAttempt : null;
  const level = latest?.level ?? "unknown";
  const canAcknowledge = can(me, "review");
  const canSurvey = can(me, "survey");
  const hasSignals = latest?.status === "ok" && latest.signals.length > 0;

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-2">
        <Link href="/dashboard/watch" className="w-fit text-sm text-mud hover:text-sadu">
          → كل المواقع
        </Link>
        <div className="flex flex-wrap items-center gap-3">
          <h1 ref={headingRef} tabIndex={-1} className="text-3xl font-bold">
            {site.name_ar}
          </h1>
          <LevelBadge level={level} />
          {latest?.is_sample && <SampleBadge>بيانات تجريبية</SampleBadge>}
        </div>
        {latest && (
          <p className="text-sm text-mud">
            قارنّا {countAr(latest.recent_scenes, scenes)} من {dateAr(latest.recent_start)} إلى{" "}
            {dateAr(latest.recent_end)} بـ{countAr(latest.baseline_scenes, scenes)} من السنة التي قبلها ·
            الصافي منها {Math.round(latest.valid_share * 100).toLocaleString("ar-SA")}٪ من المساحة
          </p>
        )}
      </header>

      {warningAr(site) && (
        <p
          className={`rounded-sm border p-3 ${site.alert ? "border-urgent/40 bg-urgent/5" : "border-line bg-white"}`}
        >
          {site.alert && (
            <strong>
              <TriangleAlertIcon className="me-1 inline size-4 align-[-0.125em] text-urgent" aria-hidden="true" />
              تنبيه للمختصين ·{" "}
            </strong>
          )}
          {warningAr(site)}
          {site.trend && site.trend !== "new" && <> · {trendAr[site.trend]}</>}
        </p>
      )}

      {error && (
        <p role="alert" className="rounded-sm border border-urgent/40 bg-urgent/5 p-3 text-sm">
          {error}
        </p>
      )}

      <div className="flex flex-col gap-3">
        <div className="flex flex-wrap gap-2">
          {canSurvey && (
            <Button
              type="button"
              variant="outline"
              onClick={() =>
                run("scan", async () => {
                  await scanSite(siteId);
                  return { kind: "scan" };
                })
              }
              disabled={busy !== null}
            >
              {busy === "scan" ? "يُفحص…" : "افحص الآن"}
            </Button>
          )}
          {canSurvey && hasSignals && latest && !latest.ground_check_at && (
            <Button
              type="button"
              onClick={() => run("ground", async () => ({ kind: "ground", check: await requestGroundCheck(latest.id) }))}
              disabled={busy !== null}
            >
              {busy === "ground" ? "يُرسل…" : "اطلب تحققًا ميدانيًا"}
            </Button>
          )}
          {hasSignals && latest && canAcknowledge && !latest.acknowledged_at && (
            <Button
              type="button"
              variant="outline"
              onClick={() =>
                run("ack", async () => {
                  await acknowledgeScan(latest.id);
                  return { kind: "ack" };
                })
              }
              disabled={busy !== null}
            >
              {busy === "ack" ? "يُحفظ…" : "أكّد أنك راجعت التنبيه"}
            </Button>
          )}
        </div>
        <div role="status">{notice && <NoticeText notice={notice} />}</div>
      </div>

      {latest?.ground_check_at && notice?.kind !== "ground" && (
        <p className="text-sm text-mud">طُلب التحقق الميداني في {dateAr(latest.ground_check_at)}.</p>
      )}

      {failedSince && (
        <p className="rounded-sm border border-line bg-white p-4">
          آخر محاولة في {dateAr(failedSince.created_at)}: {statusAr[failedSince.status]}.
          {latest && " نعرض أدناه آخر فحص مكتمل."}
        </p>
      )}
      {latest === null && !failedSince && (
        <p className="rounded-sm border border-line bg-white p-4">لم يُفحص هذا الموقع بعد. ابدأ بفحص الآن.</p>
      )}

      {latest?.status === "ok" && (
        <div className="grid gap-6 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]">
          <CompareImages scan={latest} colors={overview.threat_colors} />
          <section className="flex flex-col gap-3" aria-labelledby="signals-title">
            <h2 id="signals-title" className="text-lg font-bold">
              ما الذي تغيّر
            </h2>
            {latest.signals.length === 0 ? (
              <p className="text-mud">لا تغيّر ملحوظ داخل الموقع ولا في محيطه.</p>
            ) : (
              <ul className="flex flex-col divide-y divide-line rounded-sm border border-line bg-white">
                {[...latest.signals]
                  .sort((a, b) => b.area_m2 - a.area_m2)
                  .map((signal) => (
                    <li
                      key={`${signal.threat}-${signal.zone}`}
                      className="flex items-start gap-3 p-3"
                    >
                      <span
                        className="mt-1.5 inline-block size-3 shrink-0 rounded-sm"
                        style={{ background: overview.threat_colors[signal.threat] }}
                      />
                      <div>
                        <p className="font-bold">{threatAr[signal.threat]}</p>
                        <p className="text-sm text-mud">
                          {zoneAr[signal.zone]} · <bdi className="whitespace-nowrap">{areaAr(signal.area_m2)}</bdi> (
                          {Math.round((signal.changed_pixels / signal.zone_pixels) * 100).toLocaleString("ar-SA")}٪)
                        </p>
                      </div>
                    </li>
                  ))}
              </ul>
            )}
            <p className="text-xs text-mud">
              دقة الصور <span className="whitespace-nowrap">١٠{"\u00a0"}م</span> للبكسل: تكشف البناء والحفر والمياه وإزالة النخيل، ولا تكشف شقوق الجدران. ذلك عمل
              التصوير الأرضي.
            </p>
          </section>
        </div>
      )}

      {scans.some((scan) => scan.id !== latest?.id) && (
        <section className="flex flex-col gap-2" aria-labelledby="history-title">
          <h2 id="history-title" className="text-lg font-bold">
            الفحوص السابقة
          </h2>
          <ol className="flex flex-col divide-y divide-line rounded-sm border border-line bg-white">
            {scans.filter((scan) => scan.id !== latest?.id).map((scan) => {
              const strongest = strongestSignal(scan);
              return (
                <li key={scan.id} className="flex flex-wrap items-center gap-3 px-3 py-2 text-sm">
                  <time dateTime={scan.created_at} className="tabular-nums text-mud">
                    {dateAr(scan.created_at)}
                  </time>
                  <LevelBadge level={scan.level} />
                  <span>
                    {scan.status !== "ok"
                      ? statusAr[scan.status]
                      : strongest
                        ? <>{threatAr[strongest.threat]} · <bdi className="whitespace-nowrap">{areaAr(strongest.area_m2)}</bdi></>
                        : "لا تغيّر ملحوظ"}
                  </span>
                </li>
              );
            })}
          </ol>
        </section>
      )}

      <CopernicusCredit scan={latest} />
    </div>
  );
}

function NoticeText({ notice }: { notice: Notice }) {
  if (notice.kind === "scan") return <p className="rounded-sm border border-line bg-white p-3">انتهى الفحص، والنتيجة أدناه.</p>;
  if (notice.kind === "ack") return <p className="rounded-sm border border-line bg-white p-3">سُجّلت مراجعتك للتنبيه.</p>;
  const { check } = notice;
  return (
    <p className="rounded-sm border border-line bg-white p-3">
      {check.inspector_visit
        ? "لا توجد واجهات بصور مرجعية لهذا الموقع، لذلك يحتاج زيارة مفتش."
        : check.mission_ids.length === 0
          ? "مهام التصوير مفتوحة مسبقًا على واجهات هذا الموقع."
          : `فُتحت ${countAr(check.mission_ids.length, missions)} للزوار حول الواجهات.`}{" "}
      {!check.inspector_visit && (
        <Link href="/dashboard" className="font-bold text-sadu underline">
          تابع المهام
        </Link>
      )}
    </p>
  );
}
