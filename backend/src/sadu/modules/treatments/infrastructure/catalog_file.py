from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field, HttpUrl

from sadu.modules.treatments.domain.models import Catalog, Material, ReviewStatus, Source, Treatment
from sadu.shared.vocabulary import DamageType, Severity


class SourceFile(BaseModel):
    id: str
    title: str
    url: HttpUrl


class MaterialFile(BaseModel):
    name_ar: str
    name_en: str
    unit_ar: str
    per_m2: float = Field(ge=0)


class TreatmentFile(BaseModel):
    code: str
    damage_type: DamageType
    severities: list[Severity] = Field(min_length=1)
    title_ar: str
    steps_ar: list[str] = Field(min_length=1)
    materials: list[MaterialFile] = Field(default_factory=list)
    tools_ar: list[str] = Field(default_factory=list)
    specialist_required: bool
    sources: list[str] = Field(min_length=1)


class CatalogFile(BaseModel):
    version: str
    review_status: ReviewStatus
    reviewed_by: str | None = None
    quantities_note_ar: str
    sources: list[SourceFile]
    treatments: list[TreatmentFile]


@lru_cache
def load_catalog(path: Path) -> Catalog:
    parsed = CatalogFile.model_validate_json(path.read_text(encoding="utf-8"))
    return Catalog(
        version=parsed.version,
        review_status=parsed.review_status,
        reviewed_by=parsed.reviewed_by,
        quantities_note_ar=parsed.quantities_note_ar,
        sources={s.id: Source(s.id, s.title, str(s.url)) for s in parsed.sources},
        treatments=tuple(
            Treatment(
                code=t.code,
                damage_type=t.damage_type,
                severities=frozenset(t.severities),
                title_ar=t.title_ar,
                steps_ar=tuple(t.steps_ar),
                materials=tuple(Material(m.name_ar, m.name_en, m.unit_ar, m.per_m2) for m in t.materials),
                tools_ar=tuple(t.tools_ar),
                specialist_required=t.specialist_required,
                source_ids=tuple(t.sources),
            )
            for t in parsed.treatments
        ),
    )
