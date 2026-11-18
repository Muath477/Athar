from dataclasses import dataclass
from enum import StrEnum

from sadu.shared.vocabulary import DamageType


class Geometry(StrEnum):
    AREA = "area"
    LINE = "line"
    POINT = "point"


class ClassKind(StrEnum):
    WIDTH = "width"
    DEPTH = "depth"
    SIZE = "size"


class WidthClass(StrEnum):
    UNDER_1MM = "under_1mm"
    FROM_1_TO_5MM = "from_1_to_5mm"
    OVER_5MM = "over_5mm"


class DepthClass(StrEnum):
    SHALLOW = "shallow"
    MEDIUM = "medium"
    DEEP = "deep"


class SizeClass(StrEnum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


CLASS_VALUES: dict[ClassKind, tuple[str, ...]] = {
    ClassKind.WIDTH: tuple(WidthClass),
    ClassKind.DEPTH: tuple(DepthClass),
    ClassKind.SIZE: tuple(SizeClass),
}


@dataclass(frozen=True)
class GlossaryEntry:
    damage_type: DamageType
    name_ar: str
    geometry: Geometry
    measure_ar: str
    class_kind: ClassKind | None = None
    core: bool = True


GLOSSARY: dict[DamageType, GlossaryEntry] = {
    entry.damage_type: entry
    for entry in (
        GlossaryEntry(DamageType.PLASTER_LOSS, "فقدان اللياسة", Geometry.AREA, "المساحة بالمتر المربع"),
        GlossaryEntry(
            DamageType.CRACK, "التشققات", Geometry.LINE, "الطول بالمتر وفئة العرض", ClassKind.WIDTH
        ),
        GlossaryEntry(
            DamageType.BASAL_EROSION,
            "تآكل القاعدة",
            Geometry.AREA,
            "الامتداد بالمتر وفئة العمق",
            ClassKind.DEPTH,
        ),
        GlossaryEntry(
            DamageType.RAIN_GULLY, "أخاديد الأمطار", Geometry.LINE, "الطول بالمتر وفئة العمق", ClassKind.DEPTH
        ),
        GlossaryEntry(DamageType.SALT_EFFLORESCENCE, "تزهّر الأملاح", Geometry.AREA, "المساحة المتأثرة"),
        GlossaryEntry(DamageType.CAVITY, "الفجوات والجحور", Geometry.POINT, "العدد والحجم", ClassKind.SIZE),
        GlossaryEntry(
            DamageType.WALL_HEAD, "تلف رؤوس الجدران والشرفات", Geometry.AREA, "المساحة بالمتر المربع"
        ),
        GlossaryEntry(
            DamageType.CEMENT_REPAIR, "ترميمات إسمنتية سابقة", Geometry.AREA, "المساحة بالمتر المربع"
        ),
        GlossaryEntry(DamageType.MOISTURE, "رطوبة", Geometry.AREA, "المساحة بالمتر المربع", core=False),
        GlossaryEntry(
            DamageType.SURFACE_EROSION, "تآكل السطح", Geometry.AREA, "المساحة بالمتر المربع", core=False
        ),
        GlossaryEntry(
            DamageType.PARTIAL_COLLAPSE, "انهيار جزئي", Geometry.AREA, "المساحة بالمتر المربع", core=False
        ),
        GlossaryEntry(DamageType.GRAFFITI, "كتابات", Geometry.AREA, "المساحة بالمتر المربع", core=False),
    )
}


def entry_for(damage_type: DamageType) -> GlossaryEntry:
    entry = GLOSSARY.get(damage_type)
    if entry is None:
        raise ValueError(f"{damage_type} is not in the wall glossary")
    return entry
