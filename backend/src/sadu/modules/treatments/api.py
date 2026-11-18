from pathlib import Path

from sadu.modules.treatments.domain.models import Catalog, Material, ReviewStatus, Source, Treatment
from sadu.modules.treatments.domain.planning import (
    DamagedArea,
    MaterialNeed,
    PlanItem,
    TreatmentPlan,
    plan_treatments,
)
from sadu.modules.treatments.infrastructure.catalog_file import load_catalog

__all__ = [
    "Catalog",
    "DamagedArea",
    "Material",
    "MaterialNeed",
    "PlanItem",
    "ReviewStatus",
    "Source",
    "Treatment",
    "TreatmentPlan",
    "catalog_at",
    "plan_treatments",
]


def catalog_at(path: Path) -> Catalog:
    return load_catalog(path.resolve())
