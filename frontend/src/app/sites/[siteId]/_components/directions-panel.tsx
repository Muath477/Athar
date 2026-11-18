"use client";

import { useState } from "react";
import type { Site } from "@/lib/api";
import { directionsUrl, type TravelMode, travelModeAr } from "@/lib/directions";

const MODES: TravelMode[] = ["walking", "driving"];

type Props = { site: Site; mode: TravelMode; onModeChange: (mode: TravelMode) => void };

export function DirectionsPanel({ site, mode, onModeChange }: Props) {
  const [copied, setCopied] = useState(false);
  const coordinates = `${site.location.lat.toFixed(5)}, ${site.location.lon.toFixed(5)}`;

  async function copyCoordinates() {
    try {
      await navigator.clipboard.writeText(coordinates);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  }

  return (
    <section className="flex flex-col gap-4 rounded-xl border border-clay/40 p-4" aria-labelledby="directions-title">
      <h2 id="directions-title" className="text-xl font-bold">
        طريق الوصول
      </h2>

      <fieldset className="flex flex-col gap-2">
        <legend className="mb-1 text-sm">كيف ستصل؟</legend>
        <div className="flex gap-2">
          {MODES.map((option) => (
            <label
              key={option}
              className="flex min-h-11 cursor-pointer items-center rounded-full border border-mud px-4 has-[:checked]:bg-mud has-[:checked]:text-sand has-[:focus-visible]:outline has-[:focus-visible]:outline-3 has-[:focus-visible]:outline-sadu"
            >
              <input
                type="radio"
                name="travel-mode"
                value={option}
                checked={mode === option}
                onChange={() => onModeChange(option)}
                className="sr-only"
              />
              {travelModeAr[option]}
            </label>
          ))}
        </div>
      </fieldset>

      <a
        href={directionsUrl(site.location, mode)}
        target="_blank"
        rel="noreferrer"
        className="min-h-12 self-start content-center rounded-full bg-sadu px-6 text-lg font-bold text-sand shadow"
      >
        افتح الاتجاهات في Google Maps
      </a>
      <p className="text-sm leading-relaxed">
        يحسب Google Maps الطريق من موقعك داخل تطبيقه، ولا يصلنا موقعك.
      </p>

      <div className="flex flex-wrap items-center gap-3 border-t border-clay/30 pt-3 text-sm">
        <span>الإحداثيات</span>
        <bdi dir="ltr" className="tabular-nums">
          {coordinates}
        </bdi>
        <button onClick={copyCoordinates} className="min-h-11 rounded-full border border-ink px-4">
          {copied ? "نُسخت" : "انسخ"}
        </button>
      </div>
    </section>
  );
}
