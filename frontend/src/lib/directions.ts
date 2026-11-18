import type { LatLon } from "./api";

export type TravelMode = "walking" | "driving";

export const travelModeAr: Record<TravelMode, string> = { walking: "مشيًا", driving: "بالسيارة" };

const GOOGLE_TRAVEL_MODE: Record<TravelMode, "WALKING" | "DRIVING"> = { walking: "WALKING", driving: "DRIVING" };

export function googleTravelMode(mode: TravelMode): "WALKING" | "DRIVING" {
  return GOOGLE_TRAVEL_MODE[mode];
}

export function directionsUrl(destination: LatLon, mode: TravelMode): string {
  const params = new URLSearchParams({
    api: "1",
    destination: `${destination.lat},${destination.lon}`,
    travelmode: mode,
  });
  return `https://www.google.com/maps/dir/?${params}`;
}

export function placeUrl(place: LatLon): string {
  const params = new URLSearchParams({ api: "1", query: `${place.lat},${place.lon}` });
  return `https://www.google.com/maps/search/?${params}`;
}

const arabicNumber = new Intl.NumberFormat("ar-SA", { maximumFractionDigits: 1 });

export function distanceAr(meters: number): string {
  if (meters < 1000) return `${arabicNumber.format(Math.round(meters / 10) * 10)} م`;
  return `${arabicNumber.format(meters / 1000)} كم`;
}

export function durationAr(millis: number): string {
  const minutes = Math.max(1, Math.round(millis / 60000));
  if (minutes < 60) return `${arabicNumber.format(minutes)} دقيقة`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest === 0 ? `${arabicNumber.format(hours)} ساعة` : `${arabicNumber.format(hours)} ساعة و${arabicNumber.format(rest)} دقيقة`;
}
