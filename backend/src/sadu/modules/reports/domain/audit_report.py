from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class AuditPhoto:
    jpeg: bytes
    caption: str


@dataclass(frozen=True)
class AuditElement:
    wall_name: str
    id: str
    damage_type: str
    location: str
    severity: str
    confidence: str
    damage_class: str | None
    area_m2: float
    length_m: float
    count: int
    measured: bool
    needs_field_visit: bool


@dataclass(frozen=True)
class AuditTreatment:
    title_ar: str
    damage_type: str
    severity: str
    specialist_required: bool


@dataclass(frozen=True)
class AuditReport:
    title_ar: str
    reference: str
    generated_at: datetime
    site_names: tuple[str, ...]
    summary_ar: str
    photos: tuple[AuditPhoto, ...]
    elements: tuple[AuditElement, ...]
    treatments: tuple[AuditTreatment, ...]
    recommendations_ar: tuple[str, ...]
    documents: tuple[str, ...]
    draft_map_ids: tuple[str, ...]

    @property
    def urgent(self) -> int:
        return sum(1 for e in self.elements if e.severity == "urgent")

    @property
    def field_visits(self) -> tuple[AuditElement, ...]:
        return tuple(e for e in self.elements if e.needs_field_visit)
