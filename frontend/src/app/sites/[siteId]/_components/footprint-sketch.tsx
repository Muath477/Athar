import type { LatLon } from "@/lib/api";

const SIZE = 100;
const PADDING = 14;

export function FootprintSketch({ boundary }: { boundary: LatLon[] }) {
  const points = projectToBox(boundary);
  if (points.length < 3) return null;

  return (
    <svg viewBox={`0 0 ${SIZE} ${SIZE}`} className="size-32 text-mud" aria-hidden>
      <g stroke="currentColor" strokeOpacity={0.18} strokeWidth={0.4}>
        {[25, 50, 75].map((line) => (
          <g key={line}>
            <line x1={line} y1={0} x2={line} y2={SIZE} />
            <line x1={0} y1={line} x2={SIZE} y2={line} />
          </g>
        ))}
      </g>
      <polygon
        points={points.map(([x, y]) => `${x},${y}`).join(" ")}
        className="fill-clay/40 stroke-sadu"
        strokeWidth={1.6}
        strokeLinejoin="round"
      />
      <path d="M50 4 L53 11 L47 11 Z" className="fill-ink" />
    </svg>
  );
}

function projectToBox(boundary: LatLon[]): [number, number][] {
  if (boundary.length === 0) return [];
  const meanLat = boundary.reduce((sum, p) => sum + p.lat, 0) / boundary.length;
  const shrink = Math.cos((meanLat * Math.PI) / 180);
  const xs = boundary.map((p) => p.lon * shrink);
  const ys = boundary.map((p) => p.lat);
  const [minX, maxX, minY, maxY] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
  const span = Math.max(maxX - minX, maxY - minY) || 1;
  const scale = (SIZE - PADDING * 2) / span;
  const offsetX = (SIZE - (maxX - minX) * scale) / 2;
  const offsetY = (SIZE - (maxY - minY) * scale) / 2;
  return boundary.map((_, i) => [
    round(offsetX + (xs[i] - minX) * scale),
    round(SIZE - offsetY - (ys[i] - minY) * scale),
  ]);
}

function round(value: number): number {
  return Math.round(value * 10) / 10;
}
