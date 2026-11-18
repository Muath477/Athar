from dataclasses import dataclass
from enum import StrEnum


class StepState(StrEnum):
    DONE = "done"
    FLAGGED = "flagged"
    WAITING = "waiting"
    BLOCKED = "blocked"


class Actor(StrEnum):
    AGENT = "agent"
    SPECIALIST = "specialist"


class Criterion(StrEnum):
    NONE = "none"
    PRIVACY = "privacy"
    ACCURACY = "accuracy"
    REVIEWABILITY = "reviewability"
    MAP_CLARITY = "map_clarity"


@dataclass(frozen=True)
class WorkflowFacts:
    elements: int
    low_confidence: int
    treatments_matched: int
    treatments_unmatched: int
    material_lines: int
    corrections: int
    field_inspected: bool
    approved: bool


@dataclass(frozen=True)
class Step:
    number: int
    key: str
    title_ar: str
    actor: Actor
    criterion: Criterion
    state: StepState
    output_ar: str


ARABIC_DIGITS = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")


def _ar(number: int) -> str:
    return str(number).translate(ARABIC_DIGITS)


def workflow(facts: WorkflowFacts) -> tuple[Step, ...]:
    review_state = StepState.DONE if facts.approved else StepState.WAITING
    approval_state = (
        StepState.DONE
        if facts.approved
        else (StepState.WAITING if facts.field_inspected else StepState.BLOCKED)
    )
    return (
        Step(1, "photo_check", "فحص الصورة", Actor.AGENT, Criterion.NONE, StepState.DONE, "صورة مقبولة"),
        Step(
            2,
            "privacy",
            "إخفاء الوجوه",
            Actor.AGENT,
            Criterion.PRIVACY,
            StepState.DONE,
            "تُطمس الوجوه وتُحذف بيانات الموقع من الصورة قبل التحليل والتخزين",
        ),
        Step(
            3,
            "detect",
            "تحديد التلف",
            Actor.AGENT,
            Criterion.ACCURACY,
            StepState.DONE,
            f"عناصر تلف مصنفة من المسرد: {_ar(facts.elements)}",
        ),
        Step(
            4,
            "confidence",
            "تقدير الثقة",
            Actor.AGENT,
            Criterion.REVIEWABILITY,
            StepState.FLAGGED if facts.low_confidence else StepState.DONE,
            f"عناصر منخفضة الثقة تنتظر المختص: {_ar(facts.low_confidence)}"
            if facts.low_confidence
            else "كل العناصر بثقة كافية",
        ),
        Step(
            5,
            "treatment",
            "اقتراح المعالجة",
            Actor.AGENT,
            Criterion.ACCURACY,
            StepState.FLAGGED if facts.treatments_unmatched else StepState.DONE,
            f"معالجات من المكتبة المعتمدة: {_ar(facts.treatments_matched)}"
            + (
                f"، و{_ar(facts.treatments_unmatched)} بلا معالجة في المكتبة"
                if facts.treatments_unmatched
                else ""
            ),
        ),
        Step(
            6,
            "materials",
            "المواد والأدوات",
            Actor.AGENT,
            Criterion.ACCURACY,
            StepState.DONE,
            f"بنود مواد مرتبطة بمواقع التلف: {_ar(facts.material_lines)}",
        ),
        Step(
            7,
            "unified_map",
            "الخريطة الموحدة",
            Actor.AGENT,
            Criterion.MAP_CLARITY,
            StepState.DONE,
            "خريطة وجدول",
        ),
        Step(
            8,
            "specialist_review",
            "مراجعة المختص",
            Actor.SPECIALIST,
            Criterion.REVIEWABILITY,
            review_state,
            f"تصحيحات محفوظة في السجل: {_ar(facts.corrections)}",
        ),
        Step(
            9,
            "approval",
            "الاعتماد",
            Actor.SPECIALIST,
            Criterion.REVIEWABILITY,
            approval_state,
            "قرار موثّق"
            if facts.approved
            else ("ينتظر قرار المختص" if facts.field_inspected else "يتطلب فحصًا ميدانيًا قبل الاعتماد"),
        ),
        Step(
            10,
            "outputs",
            "المخرجات المعتمدة",
            Actor.AGENT,
            Criterion.NONE,
            StepState.DONE if facts.approved else StepState.WAITING,
            "خريطة · جدول · سجل تصحيحات" if facts.approved else "تُصدر بعد الاعتماد",
        ),
    )
