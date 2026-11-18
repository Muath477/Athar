"use client";

import { XIcon } from "lucide-react";
import { SeverityLabel } from "@/components/brand/severity-label";
import { Button } from "@/components/ui/button";
import type { Finding } from "@/lib/api";
import { damageTypeAr, findingLabelAr } from "@/lib/labels";

export function EvidencePanel({ finding, onClose }: { finding: Finding; onClose?: () => void }) {
  const images = [
    { title: "الصورة المرجعية", url: finding.evidence?.baseline_url },
    { title: "الصورة الجديدة بعد المحاذاة", url: finding.evidence?.photo_url },
    { title: "خريطة الفرق", url: finding.evidence?.diff_url },
  ];
  return (
    <aside className="flex flex-col gap-3 rounded-sm border border-line bg-white p-4">
      <div className="flex items-start justify-between gap-2">
        <h2 className="text-lg font-bold">
          {damageTypeAr[finding.damage_type] ?? finding.damage_type} · <SeverityLabel severity={finding.severity} />
        </h2>
        {onClose && (
          <Button type="button" variant="ghost" size="icon" onClick={onClose} aria-label="أغلق" className="-mt-2 -me-2">
            <XIcon className="size-5" aria-hidden="true" />
          </Button>
        )}
      </div>
      <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-sm">
        <dt>درجة الثقة</dt>
        <dd>{findingLabelAr[finding.label]}</dd>
        <dt>تأكيدات مستقلة</dt>
        <dd>{finding.confirmations.toLocaleString("ar-SA")}</dd>
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
              <img src={image.url} alt={image.title} className="rounded-lg" />
              <figcaption className="text-xs">{image.title}</figcaption>
            </figure>
          ) : null,
        )}
      </div>
    </aside>
  );
}
