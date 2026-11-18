from datetime import datetime

from sadu.modules.mapping import api as mapping
from sadu.modules.reports.application.site_condition import SiteCondition
from sadu.modules.reports.domain.arabic import (
    CLASS_AR,
    CONFIDENCE_AR,
    DAMAGE_TYPE_AR,
    REPORT_ZONE,
    SEVERITY_AR,
    SOURCE_AR,
    WALL_STATUS_AR,
)
from sadu.shared.tabular import Cell

CONDITION_HEADER = (
    "الجدار",
    "الحالة",
    "تاريخ المسح",
    "تاريخ الاعتماد",
    "تاريخ الفحص الميداني",
    "عناصر التلف",
    "العناصر العاجلة",
    "عناصر تنتظر المراجعة",
    "المساحة المتضررة (م²)",
    "يحتاج مختصًا",
    "مستحق المسح",
)

ELEMENTS_HEADER = (
    "رقم العنصر",
    "نوع التلف",
    "الفئة",
    "الخطورة",
    "الثقة",
    "المصدر",
    "الموقع على الجدار",
    "المساحة (م²)",
    "الطول (م)",
    "العدد",
)


def condition_rows(condition: SiteCondition) -> list[tuple[Cell, ...]]:
    return [
        (
            wall.name_ar,
            WALL_STATUS_AR.get(wall.status, wall.status),
            _day(wall.surveyed_at),
            _day(wall.approved_at),
            _day(wall.field_inspected_at),
            wall.elements,
            wall.urgent,
            wall.needs_review,
            round(wall.damaged_area_m2, 2),
            _yes_no(wall.needs_specialist),
            _yes_no(wall.survey_due),
        )
        for wall in condition.walls
    ]


def element_rows(view: mapping.MapView) -> list[tuple[Cell, ...]]:
    rows: list[tuple[Cell, ...]] = []
    for element in view.elements:
        size = mapping.measure(element, view.wall)
        rows.append(
            (
                element.id,
                DAMAGE_TYPE_AR.get(element.damage_type, element.damage_type),
                CLASS_AR.get(element.damage_class, element.damage_class) if element.damage_class else None,
                SEVERITY_AR.get(element.severity, element.severity),
                CONFIDENCE_AR.get(element.confidence, element.confidence),
                SOURCE_AR.get(element.source, element.source),
                mapping.location_label(element, view.grid),
                size.area_m2 or None,
                size.length_m or None,
                size.count or None,
            )
        )
    return rows


def _day(moment: datetime | None) -> str | None:
    return moment.astimezone(REPORT_ZONE).date().isoformat() if moment else None


def _yes_no(flag: bool) -> str:
    return "نعم" if flag else "لا"
