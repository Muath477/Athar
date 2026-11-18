import Link from "next/link";
import { type SiteRisk, levelAr } from "@/lib/watch";

const WIDTH = 640;
const HEIGHT = 440;
const PADDING = 36;
const MIN_SPAN_DEG = 0.2;

const LEVEL_FILL: Record<string, string> = {
  unknown: "var(--color-clay)",
  stable: "var(--color-ink)",
  watch: "var(--color-watch)",
  moderate: "var(--color-moderate)",
  urgent: "var(--color-urgent)",
};

const LEVEL_RADIUS: Record<string, number> = { unknown: 6, stable: 6, watch: 9, moderate: 11, urgent: 13 };
const LABELLED = new Set(["watch", "moderate", "urgent"]);

export function project(sites: SiteRisk[]): (lat: number, lon: number) => [number, number] {
  const lats = sites.map((s) => s.location.lat);
  const lons = sites.map((s) => s.location.lon);
  const midLat = (Math.min(...lats) + Math.max(...lats)) / 2;
  const midLon = (Math.min(...lons) + Math.max(...lons)) / 2;
  const squash = Math.cos((midLat * Math.PI) / 180);
  const spanLon = Math.max((Math.max(...lons) - Math.min(...lons)) * squash, MIN_SPAN_DEG);
  const spanLat = Math.max(Math.max(...lats) - Math.min(...lats), MIN_SPAN_DEG);
  const scale = Math.min((WIDTH - 2 * PADDING) / spanLon, (HEIGHT - 2 * PADDING) / spanLat);
  return (lat, lon) => [WIDTH / 2 + (lon - midLon) * squash * scale, HEIGHT / 2 - (lat - midLat) * scale];
}

export function RegionMap({ sites }: { sites: SiteRisk[] }) {
  if (sites.length === 0) return null;
  const toPoint = project(sites);
  const ordered = [...sites].sort((a, b) => a.priority - b.priority);

  return (
    <figure className="flex flex-col gap-2">
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        className="w-full rounded-xl bg-white/60"
        role="group"
        aria-label="مواقع المنطقة على الخريطة، ملوّنة بدرجة الخطر"
      >
        {ordered.map((site) => {
          const [x, y] = toPoint(site.location.lat, site.location.lon);
          const level = site.latest?.level ?? "unknown";
          return (
            <Link
              key={site.site_id}
              href={`/dashboard/watch/${site.site_id}`}
              aria-label={`${site.name_ar}: ${levelAr[level]}`}
              className="group outline-none"
            >
              <circle
                cx={x}
                cy={y}
                r={LEVEL_RADIUS[level] + 6}
                className="fill-transparent stroke-sadu opacity-0 group-hover:opacity-100 group-focus-visible:opacity-100"
                strokeWidth={2}
              />
              <circle cx={x} cy={y} r={LEVEL_RADIUS[level]} fill={LEVEL_FILL[level]} stroke="white" strokeWidth={1.5}>
                <title>{site.name_ar}</title>
              </circle>
              {LABELLED.has(level) && (
                <text
                  x={x}
                  y={y - LEVEL_RADIUS[level] - 5}
                  textAnchor="middle"
                  className="fill-ink text-[13px] font-bold"
                  paintOrder="stroke"
                  stroke="white"
                  strokeWidth={3}
                >
                  {site.name_ar}
                </text>
              )}
            </Link>
          );
        })}
      </svg>
      <figcaption className="text-xs text-mud">
        المواقع في مواضعها التقريبية، وتكبر النقطة مع درجة الخطر. أسماء المواقع المستقرة تظهر عند المرور عليها.
      </figcaption>
    </figure>
  );
}
