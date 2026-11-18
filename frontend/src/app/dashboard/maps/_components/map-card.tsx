import { TriangleAlertIcon } from "lucide-react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { detectorStatusAr, mapStatusAr } from "@/lib/labels";
import type { MapSummary } from "@/lib/maps";
import { countAr, urgentCells } from "@/lib/plural";

export function MapCard({ summary }: { summary: MapSummary }) {
  const share = summary.total_cells ? summary.damaged_cells / summary.total_cells : 0;
  const approved = summary.status === "approved";

  return (
    <Link
      href={`/dashboard/maps/${summary.id}`}
      className="group flex h-full flex-col overflow-hidden rounded-sm border border-line bg-white transition-colors duration-150 hover:border-ink"
    >
      <div className="relative aspect-[16/9] overflow-hidden bg-mud/20">
        <img
          src={summary.thumbnail_url}
          alt=""
          loading="lazy"
          className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-[1.03] motion-reduce:group-hover:scale-100 motion-reduce:transition-none"
        />
        <Badge variant={approved ? "ink" : "muted"} className="absolute start-2 top-2">
          {mapStatusAr[summary.status]}
        </Badge>
      </div>
      <div className="flex flex-1 flex-col gap-2 p-3">
        <h2 className="font-bold group-hover:text-sadu">{summary.wall_name}</h2>
        <div
          className="h-1.5 overflow-hidden rounded-xs bg-clay"
          role="img"
          aria-label={`نسبة الخلايا المتضررة ${Math.round(share * 100).toLocaleString("ar-SA")}٪`}
        >
          <div className="h-full bg-mud" style={{ inlineSize: `${Math.max(share * 100, share > 0 ? 3 : 0)}%` }} />
        </div>
        <p className="text-sm text-mud">
          <span className="tabular-nums">{Math.round(share * 100).toLocaleString("ar-SA")}٪</span> من الجدار متضرر
          {summary.urgent_cells > 0 && (
            <>
              {" · "}
              <span className="inline-flex items-center gap-1 font-bold text-urgent">
                <TriangleAlertIcon className="size-4" aria-hidden="true" />
                {countAr(summary.urgent_cells, urgentCells)}
              </span>
            </>
          )}
        </p>
        <p className="mt-auto text-xs text-mud">
          {new Date(summary.created_at).toLocaleDateString("ar-SA")} · {detectorStatusAr[summary.detector_status]}
        </p>
      </div>
    </Link>
  );
}
