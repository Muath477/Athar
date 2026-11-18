from fastapi import APIRouter
from pydantic import BaseModel

from sadu.modules.admin.interface.auth import Staff
from sadu.modules.treatments import api as treatments
from sadu.shared.web import State

router = APIRouter(tags=["treatments"])


class SourceOut(BaseModel):
    id: str
    title: str
    url: str


class MaterialOut(BaseModel):
    name_ar: str
    name_en: str
    unit_ar: str
    per_m2: float


class TreatmentOut(BaseModel):
    code: str
    damage_type: str
    severities: list[str]
    title_ar: str
    steps_ar: list[str]
    materials: list[MaterialOut]
    tools_ar: list[str]
    specialist_required: bool
    sources: list[SourceOut]


class CatalogOut(BaseModel):
    version: str
    review_status: str
    reviewed_by: str | None
    quantities_note_ar: str
    treatments: list[TreatmentOut]


def treatment_out(treatment: treatments.Treatment, catalog: treatments.Catalog) -> TreatmentOut:
    return TreatmentOut(
        code=treatment.code,
        damage_type=treatment.damage_type,
        severities=sorted(treatment.severities, key=lambda s: s.rank),
        title_ar=treatment.title_ar,
        steps_ar=list(treatment.steps_ar),
        materials=[
            MaterialOut(name_ar=m.name_ar, name_en=m.name_en, unit_ar=m.unit_ar, per_m2=m.per_m2)
            for m in treatment.materials
        ],
        tools_ar=list(treatment.tools_ar),
        specialist_required=treatment.specialist_required,
        sources=[_source_out(catalog.sources[s]) for s in treatment.source_ids],
    )


@router.get("/treatments/catalog")
async def get_catalog(_: Staff, state: State) -> CatalogOut:
    catalog = treatments.catalog_at(state.settings.treatment_catalog_path)
    return CatalogOut(
        version=catalog.version,
        review_status=catalog.review_status,
        reviewed_by=catalog.reviewed_by,
        quantities_note_ar=catalog.quantities_note_ar,
        treatments=[treatment_out(t, catalog) for t in catalog.treatments],
    )


def _source_out(source: treatments.Source) -> SourceOut:
    return SourceOut(id=source.id, title=source.title, url=source.url)
