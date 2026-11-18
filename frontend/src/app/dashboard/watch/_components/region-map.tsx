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
const LABELLED = new Set(["moderate", "urgent"]);
const LABEL_SIZE = 22;
const LABEL_GAP = 6;

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
  const points = ordered.map((site) => {
    const level = site.latest?.level ?? "unknown";
    const [x, y] = toPoint(site.location.lat, site.location.lon);
    return { site, level, x, y, r: LEVEL_RADIUS[level] };
  });

  return (
    <figure className="flex flex-col gap-2">
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        className="w-full rounded-xl bg-white/60"
        role="group"
        aria-label="مواقع المنطقة على الخريطة، ملوّنة بدرجة الخطر"
      >
        {points.map(({ site, level, x, y, r }) => (
          <Link
            key={site.site_id}
            href={`/dashboard/watch/${site.site_id}`}
            aria-label={`${site.name_ar}: ${levelAr[level]}`}
            className="group"
          >
            <circle
              cx={x}
              cy={y}
              r={r + 6}
              className="fill-transparent stroke-sadu opacity-0 group-hover:opacity-100 group-focus-visible:opacity-100"
              strokeWidth={3}
            />
            <circle cx={x} cy={y} r={r} fill={LEVEL_FILL[level]} stroke="white" strokeWidth={1.5}>
              <title>{site.name_ar}</title>
            </circle>
          </Link>
        ))}
        <g aria-hidden="true" className="pointer-events-none">
          {placeLabels(points).map(({ site, x, y, anchor }) => (
            <text
              key={site.site_id}
              x={x}
              y={y}
              direction="rtl"
              textAnchor={anchor}
              dominantBaseline="central"
              fontSize={LABEL_SIZE}
              className="fill-ink font-bold"
              paintOrder="stroke"
              stroke="white"
              strokeWidth={4}
            >
              {site.name_ar}
            </text>
          ))}
        </g>
      </svg>
      <figcaption className="text-xs text-mud">
        المواقع في مواضعها التقريبية، وتكبر النقطة مع درجة الخطر. تظهر على الخريطة أسماء المواقع العاجلة والمتوسطة
        فقط، وكل المواقع مرتبة بأسمائها في القائمة.
      </figcaption>
    </figure>
  );
}

type Placed = { site: SiteRisk; x: number; y: number; anchor: "start" | "end" };
type Box = { left: number; right: number; top: number; bottom: number };

function placeLabels(points: { site: SiteRisk; level: string; x: number; y: number; r: number }[]): Placed[] {
  const taken: Box[] = points.map(({ x, y, r }) => ({ left: x - r, right: x + r, top: y - r, bottom: y + r }));
  const placed: Placed[] = [];
  const byPriority = [...points].filter(({ level }) => LABELLED.has(level)).sort((a, b) => b.site.priority - a.site.priority);
  for (const { site, x, y, r } of byPriority) {
    const width = site.name_ar.length * LABEL_SIZE * 0.5;
    const top = y - LABEL_SIZE * 0.6;
    const bottom = y + LABEL_SIZE * 0.6;
    const onLeft = { left: x - r - LABEL_GAP - width, right: x - r - LABEL_GAP, top, bottom };
    const onRight = { left: x + r + LABEL_GAP, right: x + r + LABEL_GAP + width, top, bottom };
    const fits = (box: Box) =>
      box.left >= 0 &&
      box.right <= WIDTH &&
      !taken.some((t) => t.left < box.right && box.left < t.right && t.top < box.bottom && box.top < t.bottom);
    const choice = fits(onLeft) ? onLeft : fits(onRight) ? onRight : null;
    if (!choice) continue;
    taken.push(choice);
    placed.push(
      choice === onLeft
        ? { site, x: onLeft.right, y, anchor: "start" }
        : { site, x: onRight.left, y, anchor: "end" },
    );
  }
  return placed;
}
