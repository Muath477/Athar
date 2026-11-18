from dataclasses import dataclass
from enum import StrEnum

from sadu.shared.vocabulary import DamageType, Severity


class ReviewStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"


@dataclass(frozen=True)
class Source:
    id: str
    title: str
    url: str


@dataclass(frozen=True)
class Material:
    name_ar: str
    name_en: str
    unit_ar: str
    per_m2: float


@dataclass(frozen=True)
class Treatment:
    code: str
    damage_type: DamageType
    severities: frozenset[Severity]
    title_ar: str
    steps_ar: tuple[str, ...]
    materials: tuple[Material, ...]
    tools_ar: tuple[str, ...]
    specialist_required: bool
    source_ids: tuple[str, ...]


@dataclass(frozen=True)
class Catalog:
    version: str
    review_status: ReviewStatus
    reviewed_by: str | None
    quantities_note_ar: str
    sources: dict[str, Source]
    treatments: tuple[Treatment, ...]

    def __post_init__(self) -> None:
        covered: set[tuple[DamageType, Severity]] = set()
        for treatment in self.treatments:
            unknown = [s for s in treatment.source_ids if s not in self.sources]
            if unknown:
                raise ValueError(f"Treatment {treatment.code} cites unknown sources {unknown}")
            for severity in treatment.severities:
                key = (treatment.damage_type, severity)
                if key in covered:
                    raise ValueError(f"Two treatments cover {key[0]} at severity {key[1]}")
                covered.add(key)

    def treatment_for(self, damage_type: DamageType, severity: Severity) -> Treatment | None:
        for treatment in self.treatments:
            if treatment.damage_type is damage_type and severity in treatment.severities:
                return treatment
        return None
