from datetime import datetime
from zoneinfo import ZoneInfo

REPORT_ZONE = ZoneInfo("Asia/Riyadh")

DAMAGE_TYPE_AR = {
    "plaster_loss": "فقدان اللياسة",
    "crack": "التشققات",
    "basal_erosion": "تآكل القاعدة",
    "rain_gully": "أخاديد الأمطار",
    "salt_efflorescence": "تزهّر الأملاح",
    "cavity": "الفجوات والجحور",
    "wall_head": "تلف رؤوس الجدران والشرفات",
    "cement_repair": "ترميمات إسمنتية سابقة",
    "moisture": "رطوبة",
    "surface_erosion": "تآكل السطح",
    "partial_collapse": "انهيار جزئي",
    "graffiti": "كتابة على الجدار",
}

CLASS_AR = {
    "under_1mm": "أقل من ١ ملم",
    "from_1_to_5mm": "من ١ إلى ٥ ملم",
    "over_5mm": "أكثر من ٥ ملم",
    "shallow": "سطحي",
    "medium": "متوسط",
    "deep": "عميق",
    "small": "صغير",
    "large": "كبير",
}

SEVERITY_AR = {"watch": "مراقبة", "moderate": "متوسط", "urgent": "عاجل"}

SOURCE_AR = {"model": "النموذج", "expert": "الخبير"}

DETECTOR_AR = {
    "claude": "نموذج Claude للرؤية",
    "http_detection": "نموذج كشف خارجي",
    "http_cell_classification": "نموذج تصنيف خارجي",
}

CHANGE_AR = {
    "new": "تلف جديد",
    "worse": "ساء",
    "retyped": "تغيّر نوعه",
    "improved": "تحسّن",
    "resolved": "زال",
}

MONTHS_AR = (
    "يناير",
    "فبراير",
    "مارس",
    "أبريل",
    "مايو",
    "يونيو",
    "يوليو",
    "أغسطس",
    "سبتمبر",
    "أكتوبر",
    "نوفمبر",
    "ديسمبر",
)

ARABIC_DIGITS = str.maketrans("0123456789.", "٠١٢٣٤٥٦٧٨٩٫")


def digits(value: object) -> str:
    return str(value).translate(ARABIC_DIGITS)


def number(value: float, places: int = 1) -> str:
    rounded = round(value, places)
    text = f"{rounded:.{places}f}".rstrip("0").rstrip(".") if places else f"{rounded:.0f}"
    return digits(text)


def percent(share: float) -> str:
    return f"{number(share * 100, 0)}٪"


def date_ar(moment: datetime) -> str:
    if moment.tzinfo is not None:
        moment = moment.astimezone(REPORT_ZONE)
    return f"{digits(moment.day)} {MONTHS_AR[moment.month - 1]} {digits(moment.year)}م"
