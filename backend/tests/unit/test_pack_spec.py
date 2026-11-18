import pytest
from pydantic import ValidationError

from sadu.modules.sites.infrastructure.pack_import import SiteSpec

SITE = {
    "slug": "at-turaif",
    "name_ar": "حي الطريف",
    "name_en": "At-Turaif District",
    "building_type": "historic_district",
    "location": [46.572467, 24.734133],
    "boundary": [[46.57, 24.73], [46.58, 24.73], [46.58, 24.74], [46.57, 24.73]],
}


def test_a_site_may_come_without_facades():
    spec = SiteSpec.model_validate(SITE)
    assert spec.facade_map_file is None and spec.baselines == []


def test_baseline_photos_need_a_facade_map():
    baseline = {"facade_code": "north", "file": "north.jpg", "corners_px": [[0, 0], [1, 0], [1, 1], [0, 1]]}
    with pytest.raises(ValidationError, match="baseline photos need a facade map"):
        SiteSpec.model_validate({**SITE, "baselines": [baseline]})
