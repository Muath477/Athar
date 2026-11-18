"use client";

import { useEffect, useState } from "react";

const STAGES = [
  { from: 0, label: "نطمس الوجوه ونحذف بيانات الصورة" },
  { from: 2, label: "نعدّل منظور الجدار ونقسمه شبكة" },
  { from: 4, label: "نحلّل الشبكة خلية خلية" },
  { from: 20, label: "ما زال التحليل جاريًا، الجدران الكبيرة تأخذ وقتًا أطول" },
];

export function AnalysisProgress() {
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    const timer = window.setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => window.clearInterval(timer);
  }, []);

  const current = STAGES.filter((stage) => seconds >= stage.from).length - 1;

  return (
    <div className="flex aspect-[4/3] flex-col justify-center gap-4 rounded-xl bg-ink p-6 text-sand">
      <ol className="flex flex-col gap-3" aria-live="polite">
        {STAGES.slice(0, 3).map((stage, index) => (
          <li key={stage.label} className={`flex items-center gap-3 ${index > current ? "opacity-40" : ""}`}>
            <span
              aria-hidden
              className={`h-2.5 w-2.5 rounded-full ${
                index < current ? "bg-sand" : index === current ? "animate-pulse bg-watch motion-reduce:animate-none" : "border border-sand"
              }`}
            />
            {stage.label}
          </li>
        ))}
      </ol>
      {current === 3 && <p className="text-sm text-sand/80">{STAGES[3].label}</p>}
      <p className="text-sm tabular-nums text-sand/70">{seconds.toLocaleString("ar-SA")} ث</p>
    </div>
  );
}
