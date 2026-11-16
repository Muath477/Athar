"use client";

import type { Finding } from "@/lib/api";
import { damageTypeAr, findingLabelAr, severityAr } from "@/lib/labels";

export function EvidencePanel({ finding, onClose }: { finding: Finding; onClose?: () => void }) {
  const images = [
    { title: "الصورة المرجعية", url: finding.evidence?.baseline_url },
    { title: "الصورة الجديدة بعد المحاذاة", url: finding.evidence?.photo_url },
    { title: "خريطة الفرق", url: finding.evidence?.diff_url },
  ];
  return (
    <aside className="flex flex-col gap-3 rounded-xl bg-white/80 p-4">
      <div className="flex items-start justify-between">
        <h2 className="text-lg font-bold">
          {damageTypeAr[finding.damage_type] ?? finding.damage_type} · {severityAr[finding.severity]}
        </h2>
        {onClose && (
          <button onClick={onClose} aria-label="إغلاق" className="text-xl leading-none">
            ×
          </button>
        )}
      </div>
      <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-sm">
        <dt>درجة الثقة</dt>
        <dd>{findingLabelAr[finding.label]}</dd>
        <dt>تأكيدات مستقلة</dt>
        <dd>{finding.confirmations}</dd>
        <dt>التاريخ</dt>
        <dd>{new Date(finding.created_at).toLocaleDateString("ar-SA")}</dd>
        {finding.cause && (
          <>
            <dt>سبب محتمل (تفسير)</dt>
            <dd>{finding.cause}</dd>
          </>
        )}
      </dl>
      <p className="text-sm leading-relaxed">{finding.rationale_ar}</p>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
        {images.map((image) =>
          image.url ? (
            <figure key={image.title} className="flex flex-col gap-1">
              {/* eslint-disable-next-line @next/next/no-img-element -- short-lived presigned evidence URLs */}
              <img src={image.url} alt={image.title} className="rounded-lg" />
              <figcaption className="text-xs">{image.title}</figcaption>
            </figure>
          ) : null,
        )}
      </div>
    </aside>
  );
}
