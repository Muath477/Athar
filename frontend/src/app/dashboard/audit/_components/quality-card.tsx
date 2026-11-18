"use client";

import { useEffect, useState } from "react";
import {
  type QualityRatio,
  type QualityReport,
  getQualityReport,
} from "@/lib/governance";

const ROWS: {
  key: keyof Omit<
    QualityReport,
    "every_report_has_evidence" | "evidence_target"
  >;
  label: string;
  hint: string;
}[] = [
  {
    key: "findings_with_evidence",
    label: "بلاغات الزوار المنشورة ومعها دليل",
    hint: "الصورة المرجعية والصورة الجديدة وخريطة الفرق",
  },
  {
    key: "maps_with_evidence",
    label: "مخططات معتمدة ومعها دليل",
    hint: "الصورة المقوَّمة والفحص الميداني واسم المعتمِد",
  },
  {
    key: "photos_held_back",
    label: "صور أُعيدت لصاحبها",
    hint: "طُلبت صورة أخرى أو تحديد الواجهة بدل النشر",
  },
  {
    key: "findings_held_for_specialist",
    label: "نتائج حُجزت للمختص",
    hint: "تنتظر المراجعة أو رفضها المختص",
  },
  {
    key: "specialist_rejections",
    label: "مراجعات انتهت بالرفض",
    hint: "بلاغ كاذب أوقفه المختص قبل اللوحة",
  },
  {
    key: "maps_corrected_by_specialist",
    label: "مخططات عدّلها المختص قبل الاعتماد",
    hint: "تصحيحات تدخل بيانات تدريب نموذجنا",
  },
];

export function QualityCard() {
  const [report, setReport] = useState<QualityReport | null>(null);

  useEffect(() => {
    getQualityReport().then(setReport, () => setReport(null));
  }, []);

  if (!report) return null;

  return (
    <section
      aria-labelledby="quality-title"
      className="flex flex-col gap-3 border-t border-line pt-5"
    >
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 id="quality-title" className="text-xl font-bold">
          هل وصل شيء إلى اللوحة بلا دليل؟
        </h2>
        <Verdict
          value={report.every_report_has_evidence}
          missing={missingEvidence(report)}
        />
      </div>
      <table className="w-full max-w-3xl text-sm">
        <tbody>
          {ROWS.map((row) => (
            <tr key={row.key} className="border-t border-line">
              <th scope="row" className="py-2 text-start align-top font-normal">
                <span className="block font-bold">{row.label}</span>
                <span className="block text-mud">{row.hint}</span>
              </th>
              <td className="py-2 align-top tabular-nums">
                <Share ratio={report[row.key]} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function Verdict({
  value,
  missing,
}: {
  value: boolean | null;
  missing: number;
}) {
  if (value === null) return <p className="text-sm text-mud">لا بيانات بعد</p>;
  return value ? (
    <p className="text-sm font-bold text-ink">لا، كل ما وصل معه دليل</p>
  ) : (
    <p className="text-sm font-bold text-sadu">
      نعم: {missing.toLocaleString("ar-SA")} بلا دليل كامل
    </p>
  );
}

function missingEvidence(report: QualityReport): number {
  const gap = (ratio: QualityRatio) => ratio.total - ratio.hits;
  return gap(report.findings_with_evidence) + gap(report.maps_with_evidence);
}

function Share({ ratio }: { ratio: QualityRatio }) {
  if (ratio.value === null) return <span className="text-mud">لا بيانات</span>;
  return (
    <span>
      <strong>{Math.round(ratio.value * 100).toLocaleString("ar-SA")}٪</strong>{" "}
      <span className="text-mud">
        ({ratio.hits.toLocaleString("ar-SA")} من{" "}
        {ratio.total.toLocaleString("ar-SA")})
      </span>
    </span>
  );
}
