"use client";

import { useId, useState } from "react";
import type { Scan, Threat } from "@/lib/watch";
import { threatAr } from "@/lib/watch";

type View = "compare" | "change";

export function CompareImages({ scan, colors }: { scan: Scan; colors: Record<Threat, string> }) {
  const [view, setView] = useState<View>("compare");
  const [split, setSplit] = useState(50);
  const sliderId = useId();
  if (!scan.before_url || !scan.after_url || !scan.change_url) return null;
  const threats = [...new Set(scan.signals.map((s) => s.threat))];

  return (
    <section className="flex flex-col gap-3" aria-labelledby={`${sliderId}-title`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id={`${sliderId}-title`} className="text-lg font-bold">
          الصور
        </h2>
        <div role="tablist" aria-label="طريقة العرض" className="flex gap-1 rounded-full bg-white/60 p-1">
          {(
            [
              ["compare", "قبل وبعد"],
              ["change", "خريطة التغيّر"],
            ] as const
          ).map(([value, label]) => (
            <button
              key={value}
              type="button"
              role="tab"
              aria-selected={view === value}
              onClick={() => setView(value)}
              className={`rounded-full px-4 py-1.5 text-sm transition-colors ${
                view === value ? "bg-ink text-sand" : "hover:bg-clay/20"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {view === "compare" ? (
        <div className="flex flex-col gap-2" dir="ltr">
          <div className="relative aspect-square w-full max-w-xl overflow-hidden rounded-xl bg-mud/20">
            <img src={scan.before_url} alt="الموقع قبل: متوسط صور السنة الماضية" className="absolute inset-0 h-full w-full" />
            <img
              src={scan.after_url}
              alt="الموقع بعد: متوسط صور الشهر الأخير"
              className="absolute inset-0 h-full w-full"
              style={{ clipPath: `inset(0 ${100 - split}% 0 0)` }}
            />
            <div className="pointer-events-none absolute inset-y-0 w-0.5 bg-white" style={{ left: `${split}%` }} />
            <span className="absolute left-2 top-2 rounded bg-ink/70 px-2 py-0.5 text-xs text-sand">بعد</span>
            <span className="absolute right-2 top-2 rounded bg-ink/70 px-2 py-0.5 text-xs text-sand">قبل</span>
          </div>
          <label htmlFor={sliderId} className="sr-only">
            حرّك للمقارنة بين قبل وبعد
          </label>
          <input
            id={sliderId}
            type="range"
            min={0}
            max={100}
            value={split}
            onChange={(e) => setSplit(Number(e.target.value))}
            className="w-full max-w-xl accent-sadu"
          />
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          <img
            src={scan.change_url}
            alt="صورة الشهر الأخير وعليها المناطق المتغيرة ملوّنة حسب نوع التغيّر"
            className="aspect-square w-full max-w-xl rounded-xl"
          />
          <ul className="flex flex-wrap gap-3 text-sm" aria-label="مفتاح الألوان">
            {threats.map((threat) => (
              <li key={threat} className="flex items-center gap-1.5">
                <span className="inline-block size-3 rounded-sm" style={{ background: colors[threat] }} />
                {threatAr[threat]}
              </li>
            ))}
            <li className="flex items-center gap-1.5">
              <span className="inline-block size-3 rounded-sm border-2 border-white bg-mud/40" />
              حدود الموقع
            </li>
          </ul>
        </div>
      )}
    </section>
  );
}
