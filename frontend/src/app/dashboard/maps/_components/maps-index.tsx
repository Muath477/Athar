"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ApiError } from "@/lib/api";
import { detectorStatusAr, mapStatusAr } from "@/lib/labels";
import { type MapSummary, listMaps } from "@/lib/maps";
import { useMe } from "@/lib/use-me";
import { AccuracyCard } from "./accuracy-card";

export function MapsIndex() {
  const me = useMe();
  const [maps, setMaps] = useState<MapSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!me) return;
    listMaps().then(setMaps, (e) => setError(e instanceof ApiError ? e.message : "تعذر تحميل المخططات."));
  }, [me]);

  if (!me || maps === null) return <p className="pt-6">{error ?? "…"}</p>;

  return (
    <div className="flex flex-col gap-5 pt-2">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">مخططات تلف الجدران</h1>
        <Link href="/dashboard/maps/new" className="rounded-full bg-sadu px-5 py-2 font-bold text-sand">
          مخطط جديد
        </Link>
      </div>

      {maps.length === 0 ? (
        <p>لا توجد مخططات بعد. صوّر جدارًا لإنشاء أول مخطط.</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {maps.map((m) => (
            <li key={m.id}>
              <Link
                href={`/dashboard/maps/${m.id}`}
                className="flex flex-wrap items-center justify-between gap-2 rounded-xl bg-white/70 p-3"
              >
                <span className="font-bold">{m.wall_name}</span>
                <span className="text-sm">
                  {mapStatusAr[m.status]} · {damagedShare(m)} · {detectorStatusAr[m.detector_status]} ·{" "}
                  {new Date(m.created_at).toLocaleDateString("ar-SA")}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}

      <AccuracyCard />
    </div>
  );
}

function damagedShare(summary: MapSummary): string {
  if (summary.damaged_cells === 0) return "بلا تلف ظاهر";
  return `${summary.damaged_cells.toLocaleString("ar-SA")} من ${summary.total_cells.toLocaleString("ar-SA")} خلية متضررة`;
}
