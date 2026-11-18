export type Point = { lat: number; lng: number };

const EARTH_RADIUS_M = 6371008.8;

function radians(degrees: number): number {
  return (degrees * Math.PI) / 180;
}

export function metersBetween(a: Point, b: Point): number {
  const dLat = radians(b.lat - a.lat);
  const dLng = radians(b.lng - a.lng);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(radians(a.lat)) * Math.cos(radians(b.lat)) * Math.sin(dLng / 2) ** 2;
  return 2 * EARTH_RADIUS_M * Math.asin(Math.min(1, Math.sqrt(h)));
}

export function bearingDegrees(from: Point, to: Point): number {
  const y = Math.sin(radians(to.lng - from.lng)) * Math.cos(radians(to.lat));
  const x =
    Math.cos(radians(from.lat)) * Math.sin(radians(to.lat)) -
    Math.sin(radians(from.lat)) * Math.cos(radians(to.lat)) * Math.cos(radians(to.lng - from.lng));
  return ((Math.atan2(y, x) * 180) / Math.PI + 360) % 360;
}

type Projection = { segment: number; fraction: number; point: Point; offsetMeters: number };

export function projectOntoPath(path: Point[], position: Point): Projection {
  let best: Projection = { segment: 0, fraction: 0, point: path[0], offsetMeters: metersBetween(path[0], position) };
  const shrink = Math.cos(radians(position.lat));
  for (let i = 0; i < path.length - 1; i++) {
    const a = path[i];
    const b = path[i + 1];
    const dx = (b.lng - a.lng) * shrink;
    const dy = b.lat - a.lat;
    const lengthSquared = dx * dx + dy * dy;
    const t =
      lengthSquared === 0
        ? 0
        : Math.min(1, Math.max(0, (((position.lng - a.lng) * shrink) * dx + (position.lat - a.lat) * dy) / lengthSquared));
    const point = { lat: a.lat + (b.lat - a.lat) * t, lng: a.lng + (b.lng - a.lng) * t };
    const offsetMeters = metersBetween(point, position);
    if (offsetMeters < best.offsetMeters) best = { segment: i, fraction: t, point, offsetMeters };
  }
  return best;
}

export function remainingMeters(path: Point[], projection: Projection): number {
  if (path.length < 2) return 0;
  let total = metersBetween(projection.point, path[projection.segment + 1] ?? projection.point);
  for (let i = projection.segment + 1; i < path.length - 1; i++) total += metersBetween(path[i], path[i + 1]);
  return total;
}

export function pointAhead(path: Point[], projection: Projection, meters: number): Point {
  let left = meters;
  let from = projection.point;
  for (let i = projection.segment + 1; i < path.length; i++) {
    const step = metersBetween(from, path[i]);
    if (step >= left) {
      const t = step === 0 ? 0 : left / step;
      return { lat: from.lat + (path[i].lat - from.lat) * t, lng: from.lng + (path[i].lng - from.lng) * t };
    }
    left -= step;
    from = path[i];
  }
  return path[path.length - 1];
}

export function sampleAlong(path: Point[], count: number): Point[] {
  if (path.length < 2 || count < 2) return path.slice(0, 1);
  const lengths = [0];
  for (let i = 1; i < path.length; i++) lengths.push(lengths[i - 1] + metersBetween(path[i - 1], path[i]));
  const total = lengths[lengths.length - 1];
  const samples: Point[] = [];
  let segment = 1;
  for (let k = 0; k < count; k++) {
    const target = (total * k) / (count - 1);
    while (segment < path.length - 1 && lengths[segment] < target) segment++;
    const span = lengths[segment] - lengths[segment - 1];
    const t = span === 0 ? 0 : (target - lengths[segment - 1]) / span;
    const a = path[segment - 1];
    const b = path[segment];
    samples.push({ lat: a.lat + (b.lat - a.lat) * t, lng: a.lng + (b.lng - a.lng) * t });
  }
  return samples;
}
