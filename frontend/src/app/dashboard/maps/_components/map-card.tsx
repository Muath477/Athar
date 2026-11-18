import Link from "next/link";
import { detectorStatusAr, mapSourceText, mapStatusAr } from "@/lib/labels";
import type { MapSummary } from "@/lib/maps";
import { countAr, urgentCells } from "@/lib/plural";

export function MapCard({ summary }: { summary: MapSummary }) {
  const share = summary.total_cells ? summary.damaged_cells / summary.total_cells : 0;
  const approved = summary.status === "approved";

  return (
    <Link
      href={`/dashboard/maps/${summary.id}`}
      className="group flex h-full flex-col overflow-hidden rounded-xl bg-white/75 transition-shadow hover:shadow-md focus-visible:shadow-md"
    >
      <div className="relative aspect-[16/9] overflow-hidden bg-mud/20">
        <img
          src={summary.thumbnail_url}
          alt=""
          loading="lazy"
          className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-[1.03] motion-reduce:group-hover:scale-100 motion-reduce:transition-none"
        />
        <span
          className={`absolute start-2 top-2 rounded-full px-2.5 py-0.5 text-xs font-bold ${
            approved ? "bg-ink text-sand" : "bg-sand text-ink"
          }`}
        >
          {mapStatusAr[summary.status]}
        </span>
      </div>
      <div className="flex flex-1 flex-col gap-2 p-3">
        <h2 className="font-bold leading-snug group-hover:text-sadu">{summary.wall_name}</h2>
        <div
          className="h-1.5 overflow-hidden rounded-full bg-clay/25"
          role="img"
          aria-label={`نسبة الخلايا المتضررة ${Math.round(share * 100).toLocaleString("ar-SA")}٪`}
        >
          <div className="h-full rounded-full bg-mud" style={{ inlineSize: `${Math.max(share * 100, share > 0 ? 3 : 0)}%` }} />
        </div>
        <p className="text-sm text-mud">
          <span className="tabular-nums">{Math.round(share * 100).toLocaleString("ar-SA")}٪</span> من الجدار متضرر
          {summary.urgent_cells > 0 && (
            <>
              {" · "}
              <span className="font-bold text-urgent">{countAr(summary.urgent_cells, urgentCells)}</span>
            </>
          )}
        </p>
        <p className="mt-auto text-xs text-mud">
          {new Date(summary.created_at).toLocaleDateString("ar-SA")} · {detectorStatusAr[summary.detector_status]}
          {summary.source && <> · {mapSourceText(summary.source, summary.source_label)}</>}
        </p>
      </div>
    </Link>
  );
}
