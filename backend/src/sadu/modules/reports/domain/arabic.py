from datetime import datetime
from zoneinfo import ZoneInfo

REPORT_ZONE = ZoneInfo("Asia/Riyadh")

DAMAGE_TYPE_AR = {
    "crack": "تشقق",
    "plaster_loss": "تساقط اللياسة",
    "moisture": "رطوبة",
    "basal_erosion": "تآكل في أسفل الجدار",
    "surface_erosion": "تآكل السطح",
    "partial_collapse": "انهيار جزئي",
    "graffiti": "كتابة على الجدار",
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
