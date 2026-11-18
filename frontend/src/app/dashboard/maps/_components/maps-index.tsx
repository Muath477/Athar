"use client";

import { TriangleAlertIcon } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { PageSkeleton, RetryAlert } from "@/app/_components/page-status";
import { Button, buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import { type MapSummary, listMaps } from "@/lib/maps";
import { countAr, maps as mapForms, urgentCells } from "@/lib/plural";
import { useMeState } from "@/lib/use-me";
import { AccuracyCard } from "./accuracy-card";
import { MapCard } from "./map-card";

type Filter = "all" | "draft" | "approved";

const FILTERS: { value: Filter; label: string }[] = [
  { value: "all", label: "الكل" },
  { value: "draft", label: "بانتظار الاعتماد" },
  { value: "approved", label: "معتمدة" },
];

export function MapsIndex() {
  const { me, error: meError, retry: retryMe } = useMeState();
  const [maps, setMaps] = useState<MapSummary[] | null>(null);
  const [filter, setFilter] = useState<Filter>("all");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    listMaps().then(setMaps, (e) => setError(e instanceof ApiError ? e.message : "تعذر تحميل المخططات."));
  }, []);

  useEffect(() => {
    if (me) load();
  }, [me, load]);

  function retryMaps() {
    setError(null);
    load();
  }

  if (meError || error) {
    return (
      <div className="pt-6">
        <RetryAlert message={meError ?? error ?? ""} onRetry={meError ? retryMe : retryMaps} />
      </div>
    );
  }
  if (!me || maps === null) return <IndexSkeleton />;

  const drafts = maps.filter((m) => m.status === "draft").length;
  const urgent = maps.reduce((total, m) => total + m.urgent_cells, 0);
  const shown = maps.filter((m) => filter === "all" || m.status === filter);

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h1 className="text-3xl font-bold">مخططات تلف الجدران</h1>
          <p className="text-mud">
            <strong className="text-ink">{countAr(maps.length, mapForms)}</strong>
            {drafts > 0 && (
              <>
                {" · "}
                <strong className="tabular-nums text-ink">{drafts.toLocaleString("ar-SA")}</strong> بانتظار اعتماد مختص
              </>
            )}
            {urgent > 0 && (
              <>
                {" · "}
                <strong className="inline-flex items-center gap-1 text-urgent">
                  <TriangleAlertIcon className="size-4" aria-hidden="true" />
                  {countAr(urgent, urgentCells)}
                </strong>
              </>
            )}
          </p>
        </div>
        <Link href="/dashboard/maps/new" className={buttonVariants({ size: "lg" })}>
          ارسم مخطط جدار
        </Link>
      </header>

      {maps.length > 0 && (
        <div role="group" aria-label="تصفية المخططات" className="flex w-fit flex-wrap gap-1 rounded-sm border border-line p-0.5">
          {FILTERS.map((option) => (
            <Button
              key={option.value}
              type="button"
              variant="segment"
              size="sm"
              aria-pressed={filter === option.value}
              onClick={() => setFilter(option.value)}
            >
              {option.label}
            </Button>
          ))}
        </div>
      )}

      {maps.length === 0 ? (
        <section className="flex flex-col items-start gap-3 rounded-sm border border-line bg-white p-5">
          <h2 className="text-xl font-bold">ارسم أول مخطط جدار</h2>
          <p className="max-w-prose leading-relaxed">
            صوّر جدارًا طينيًا من الأمام قدر الإمكان، وحدد زواياه الأربع، ويرسم أثر مخطط التلف وخطة المعالجة. يراجعها
            المختص قبل الاعتماد.
          </p>
          <Link href="/dashboard/maps/new" className="font-bold text-sadu underline underline-offset-4">
            ابدأ بأول جدار
          </Link>
        </section>
      ) : shown.length === 0 ? (
        <p className="text-mud">لا مخططات في هذا التصنيف.</p>
      ) : (
        <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {shown.map((summary) => (
            <li key={summary.id}>
              <MapCard summary={summary} />
            </li>
          ))}
        </ul>
      )}

      <AccuracyCard />
    </div>
  );
}

function IndexSkeleton() {
  return (
    <PageSkeleton>
      <Skeleton className="h-9 w-72 max-w-full animate-none" />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} className="aspect-[4/3] animate-none" />
        ))}
      </div>
    </PageSkeleton>
  );
}
