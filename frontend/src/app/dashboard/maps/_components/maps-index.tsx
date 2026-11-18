"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ApiError } from "@/lib/api";
import { type MapSummary, listMaps } from "@/lib/maps";
import { countAr, maps as mapForms, urgentCells } from "@/lib/plural";
import { useMe } from "@/lib/use-me";
import { AccuracyCard } from "./accuracy-card";
import { MapCard } from "./map-card";

type Filter = "all" | "draft" | "approved";

const FILTERS: { value: Filter; label: string }[] = [
  { value: "all", label: "الكل" },
  { value: "draft", label: "بانتظار الاعتماد" },
  { value: "approved", label: "معتمدة" },
];

export function MapsIndex() {
  const me = useMe();
  const [maps, setMaps] = useState<MapSummary[] | null>(null);
  const [filter, setFilter] = useState<Filter>("all");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!me) return;
    listMaps().then(setMaps, (e) => setError(e instanceof ApiError ? e.message : "تعذر تحميل المخططات."));
  }, [me]);

  if (error) return <p role="alert" className="pt-6">{error}</p>;
  if (!me || maps === null) return <IndexSkeleton />;

  const drafts = maps.filter((m) => m.status === "draft").length;
  const urgent = maps.reduce((total, m) => total + m.urgent_cells, 0);
  const shown = maps.filter((m) => filter === "all" || m.status === filter);

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h1 className="text-3xl font-bold leading-tight">مخططات تلف الجدران</h1>
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
                <strong className="text-urgent">{countAr(urgent, urgentCells)}</strong>
              </>
            )}
          </p>
        </div>
        <Link
          href="/dashboard/maps/new"
          className="rounded-full bg-sadu px-6 py-2.5 font-bold text-sand transition-transform hover:-translate-y-0.5 active:translate-y-0"
        >
          ارسم مخطط جدار
        </Link>
      </header>

      {maps.length > 0 && (
        <div role="tablist" aria-label="تصفية المخططات" className="flex w-fit gap-1 rounded-full bg-white/60 p-1">
          {FILTERS.map((option) => (
            <button
              key={option.value}
              type="button"
              role="tab"
              aria-selected={filter === option.value}
              onClick={() => setFilter(option.value)}
              className={`rounded-full px-4 py-1.5 text-sm transition-colors ${
                filter === option.value ? "bg-ink text-sand" : "hover:bg-clay/20"
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
      )}

      {maps.length === 0 ? (
        <section className="flex flex-col items-start gap-3 border-s-4 border-sadu bg-white/60 p-5">
          <h2 className="text-xl font-bold">لا توجد مخططات بعد</h2>
          <p className="max-w-prose leading-relaxed">
            صوّر جدارًا طينيًا من الأمام قدر الإمكان، وحدد زواياه الأربع، ويرسم أثر خريطة التلف وخطة المعالجة. يراجعها
            المختص قبل الاعتماد.
          </p>
          <Link href="/dashboard/maps/new" className="font-bold text-sadu underline underline-offset-4">
            ابدأ بأول جدار
          </Link>
        </section>
      ) : shown.length === 0 ? (
        <p className="text-mud">لا توجد مخططات في هذا التصنيف.</p>
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
    <div aria-busy="true" aria-label="جارٍ تحميل المخططات" className="flex flex-col gap-6">
      <div className="h-9 w-72 animate-pulse rounded bg-clay/25" />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {[0, 1, 2].map((i) => (
          <div key={i} className="aspect-[4/3] animate-pulse rounded-xl bg-clay/20" />
        ))}
      </div>
    </div>
  );
}
