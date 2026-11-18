from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from sadu.modules.assistant.domain.arabic_text import digits_ar, elements_ar
from sadu.modules.reports import api as reports
from sadu.modules.treatments import api as treatments
from sadu.shared.vocabulary import DamageType, Severity

MAX_REPORT_PHOTOS = 4
MAX_RECOMMENDATIONS = 12
MAX_RECOMMENDATION_CHARS = 500
MAX_SUMMARY_CHARS = 3000
DEFAULT_TITLE = "ملف تدقيق حالة جدار"


def build_audit_report(
    results: Sequence[dict[str, Any]],
    *,
    catalog: treatments.Catalog,
    photos: Mapping[str, bytes],
    documents: Sequence[str],
    title_ar: str | None,
    summary_ar: str | None,
    recommendations_ar: Sequence[str],
    reference: str,
    generated_at: datetime,
) -> reports.AuditReport:
    elements = tuple(
        _element(result["wall_name"], row, measured=bool(result.get("measured")))
        for result in results
        for row in result["elements"]
    )
    field_visits = [e for e in elements if e.needs_field_visit]
    recommendations = [r[:MAX_RECOMMENDATION_CHARS] for r in recommendations_ar][:MAX_RECOMMENDATIONS]
    return reports.AuditReport(
        title_ar=title_ar or _title(results),
        reference=reference,
        generated_at=generated_at,
        site_names=tuple(dict.fromkeys(r["site_name"] for r in results if r.get("site_name"))),
        summary_ar=(summary_ar or _summary(results, elements))[:MAX_SUMMARY_CHARS],
        photos=tuple(
            reports.AuditPhoto(photos[r["attachment_id"]], r["wall_name"])
            for r in results
            if r.get("attachment_id") in photos
        )[:MAX_REPORT_PHOTOS],
        elements=elements,
        treatments=_treatments(elements, catalog),
        recommendations_ar=tuple(recommendations or _default_recommendations(field_visits)),
        documents=tuple(documents),
        draft_map_ids=tuple(
            r["map_id"] for r in results if r.get("map_id") and r.get("status") != "approved"
        ),
    )


def _element(wall_name: str, row: dict[str, Any], *, measured: bool) -> reports.AuditElement:
    return reports.AuditElement(
        wall_name=wall_name,
        id=row["id"],
        damage_type=row["damage_type"],
        location=row["location"],
        severity=row["severity"],
        confidence=row["confidence"],
        damage_class=row.get("damage_class"),
        area_m2=row.get("area_m2") or 0.0,
        length_m=row.get("length_m") or 0.0,
        count=row.get("count") or 0,
        measured=measured,
        needs_field_visit=row["severity"] == Severity.URGENT or bool(row.get("needs_review")),
    )


def _treatments(
    elements: Sequence[reports.AuditElement], catalog: treatments.Catalog
) -> tuple[reports.AuditTreatment, ...]:
    pairs = dict.fromkeys((DamageType(e.damage_type), Severity(e.severity)) for e in elements)
    lines = []
    for damage_type, severity in pairs:
        treatment = catalog.treatment_for(damage_type, severity)
        if treatment is not None:
            lines.append(
                reports.AuditTreatment(
                    treatment.title_ar, damage_type.value, severity.value, treatment.specialist_required
                )
            )
    return tuple(lines)


def _title(results: Sequence[dict[str, Any]]) -> str:
    walls = list(dict.fromkeys(r["wall_name"] for r in results))
    return f"ملف تدقيق: {'، '.join(walls)}" if walls else DEFAULT_TITLE


def _summary(results: Sequence[dict[str, Any]], elements: Sequence[reports.AuditElement]) -> str:
    urgent = sum(1 for e in elements if e.severity == Severity.URGENT)
    checked = digits_ar(len(results))
    found = elements_ar(len(elements))
    return f"فُحص {checked} من الجدران والمخططات، ورُصد فيها {found}، منها {digits_ar(urgent)} عاجل."


def _default_recommendations(field_visits: Sequence[reports.AuditElement]) -> list[str]:
    recommendations = ["مراجعة المختص لكل العناصر قبل اعتماد أي مخطط أو معالجة."]
    if field_visits:
        ids = "، ".join(f"{e.wall_name} {e.id}" for e in field_visits)
        recommendations.append(f"زيارة ميدانية للتحقق من العناصر العاجلة أو منخفضة الثقة: {ids}.")
    return recommendations
