"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useState } from "react";
import { PageSkeleton, RetryAlert } from "@/app/_components/page-status";
import { SeverityLabel } from "@/components/brand/severity-label";
import { EvidencePanel } from "@/components/evidence-panel";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ApiError, type Coverage, type Finding, request, type Site } from "@/lib/api";
import { damageTypeAr, findingLabelAr } from "@/lib/labels";
import { countAr, days as dayForms } from "@/lib/plural";
import { useMeState } from "@/lib/use-me";

const SiteModel = dynamic(() => import("@/components/site-model").then((m) => m.SiteModel), {
  ssr: false,
  loading: () => <Skeleton className="h-full" />,
});

type Failure = { message: string; retry: () => void };

export function DashboardView() {
  const { me, error: meError, retry: retryMe } = useMeState();
  const [sites, setSites] = useState<Site[] | null>(null);
  const [sitesError, setSitesError] = useState<string | null>(null);
  const [siteId, setSiteId] = useState<string | null>(null);
  const [pins, setPins] = useState<Finding[]>([]);
  const [coverage, setCoverage] = useState<Coverage[]>([]);
  const [selected, setSelected] = useState<Finding | null>(null);
  const [failure, setFailure] = useState<Failure | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [requesting, setRequesting] = useState<string | null>(null);
  const [missionNotice, setMissionNotice] = useState("");
  const [missionError, setMissionError] = useState<string | null>(null);

  const loadSites = useCallback(() => {
    request<Site[]>("/sites").then(
      (list) => {
        setSites(list);
        setSiteId((current) => current ?? list[0]?.id ?? null);
      },
      (e) => setSitesError(messageOf(e, "تعذر تحميل المواقع.")),
    );
  }, []);

  useEffect(() => {
    if (me) loadSites();
  }, [me, loadSites]);

  const refresh = useCallback(
    (id: string) =>
      Promise.all([request<Finding[]>(`/sites/${id}/pins`), request<Coverage[]>(`/sites/${id}/coverage`)]).then(
        ([findings, facadeCoverage]) => {
          setPins(findings);
          setCoverage(facadeCoverage);
        },
        (e) =>
          setFailure({
            message: messageOf(e, "تعذر تحميل أضرار الموقع وتغطية واجهاته."),
            retry: () => {
              setFailure(null);
              setAttempt((n) => n + 1);
            },
          }),
      ),
    [],
  );

  useEffect(() => {
    if (siteId) refresh(siteId);
  }, [siteId, refresh, attempt]);

  function retrySites() {
    setSitesError(null);
    loadSites();
  }

  async function select(findingId: string) {
    setFailure(null);
    try {
      setSelected(await request<Finding>(`/findings/${findingId}`));
    } catch (e) {
      setFailure({ message: messageOf(e, "تعذر فتح تفاصيل الضرر."), retry: () => select(findingId) });
    }
  }

  async function dispatch(facadeId: string) {
    setRequesting(facadeId);
    setMissionError(null);
    setMissionNotice("");
    try {
      await request("/missions", { method: "POST", body: JSON.stringify({ facade_id: facadeId }) });
      setMissionNotice("فُتحت مهمة تصوير");
      if (siteId) await refresh(siteId);
    } catch (e) {
      setMissionError(messageOf(e, "تعذر فتح مهمة التصوير. أعد المحاولة."));
    } finally {
      setRequesting(null);
    }
  }

  if (meError) {
    return (
      <div className="pt-6">
        <RetryAlert message={meError} onRetry={retryMe} />
      </div>
    );
  }
  if (sitesError) {
    return (
      <div className="pt-6">
        <RetryAlert message={sitesError} onRetry={retrySites} />
      </div>
    );
  }
  if (!me || sites === null) return <OverviewSkeleton />;

  const site = sites.find((s) => s.id === siteId);

  return (
    <div className="flex flex-col gap-6 pt-2">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <h1 className="text-3xl font-bold">الموقع ثلاثي الأبعاد</h1>
        {sites.length > 0 && (
          <div className="flex w-56 flex-col gap-1.5">
            <Label htmlFor="overview-site">الموقع</Label>
            <NativeSelect id="overview-site" value={siteId ?? ""} onChange={(e) => setSiteId(e.target.value)}>
              {sites.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name_ar}
                </option>
              ))}
            </NativeSelect>
          </div>
        )}
      </header>

      {sites.length === 0 && <p className="text-mud">لا مواقع مسجلة بعد.</p>}

      {failure && <RetryAlert message={failure.message} onRetry={failure.retry} />}

      <div className="grid gap-4 lg:grid-cols-[2fr_1fr]">
        <div className="h-[420px]">
          {site && <SiteModel facades={site.facades} findings={pins} selectedId={selected?.id ?? null} onSelect={select} />}
        </div>
        <section className="flex flex-col gap-2">
          <h2 className="font-bold">الأضرار المنشورة ({pins.length.toLocaleString("ar-SA")})</h2>
          {pins.length === 0 ? (
            <p className="text-sm leading-relaxed text-mud">
              لا أضرار منشورة لهذا الموقع. تظهر هنا بعد أن يعتمدها المراجع.
            </p>
          ) : (
            <ul className="flex max-h-[380px] flex-col divide-y divide-line overflow-y-auto rounded-sm border border-line bg-white">
              {pins.map((f) => (
                <li key={f.id}>
                  <button
                    type="button"
                    onClick={() => select(f.id)}
                    aria-pressed={selected?.id === f.id}
                    className="min-h-11 w-full cursor-pointer p-3 text-start text-sm transition-colors duration-150 hover:bg-accent aria-pressed:bg-sand aria-pressed:font-bold"
                  >
                    {damageTypeAr[f.damage_type] ?? f.damage_type} · <SeverityLabel severity={f.severity} /> ·{" "}
                    {findingLabelAr[f.label]}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      {selected && <EvidencePanel finding={selected} onClose={() => setSelected(null)} />}

      <section className="flex flex-col gap-2">
        <h2 className="font-bold">تغطية الواجهات</h2>
        <p role="status" className="text-sm empty:hidden">
          {missionNotice}
        </p>
        {missionError && (
          <p role="alert" className="rounded-sm border border-urgent/40 bg-urgent/5 p-3 text-sm">
            {missionError}
          </p>
        )}
        {coverage.length === 0 ? (
          <p className="text-sm text-mud">لا واجهات مسجلة لهذا الموقع بعد.</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>الواجهة</TableHead>
                <TableHead>آخر صورة صالحة</TableHead>
                <TableHead>مهمة</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {coverage.map((c) => (
                <TableRow key={c.facade_id}>
                  <TableCell className="align-middle">{c.name_ar}</TableCell>
                  <TableCell className="align-middle">{daysAgo(c.days_since_last_photo)}</TableCell>
                  <TableCell className="align-middle">
                    {c.open_mission_id ? (
                      "مفتوحة"
                    ) : (
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => dispatch(c.facade_id)}
                        disabled={requesting !== null}
                      >
                        {requesting === c.facade_id ? "يُرسل الطلب…" : "اطلب صورة"}
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </section>
    </div>
  );
}

function OverviewSkeleton() {
  return (
    <PageSkeleton>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <Skeleton className="h-9 w-72 max-w-full animate-none" />
        <Skeleton className="h-11 w-48 animate-none" />
      </div>
      <div className="grid gap-4 lg:grid-cols-[2fr_1fr]">
        <Skeleton className="h-[420px] animate-none" />
        <Skeleton className="h-40 animate-none" />
      </div>
    </PageSkeleton>
  );
}

function messageOf(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback;
}

function daysAgo(count: number | null): string {
  if (count === null) return "لا صورة بعد";
  if (count === 0) return "اليوم";
  return `قبل ${countAr(count, dayForms)}`;
}
