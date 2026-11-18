from datetime import date

import numpy as np
import pytest

from sadu.modules.watch.domain.change import (
    ChangeReport,
    ChangeRules,
    ScreeningStatus,
    Signal,
    Threat,
    Zone,
    detect_changes,
)
from sadu.modules.watch.domain.geometry import LatLon, local_xy, zones
from sadu.modules.watch.domain.risk import RiskLevel, assess, level_for, priority
from sadu.modules.watch.domain.scene import Band, Scene, Window, median_composite

CENTRE = LatLon(24.7341, 46.5725)
WINDOW = Window(size_px=40, pixel_m=10.0)

DESERT = {
    Band.BLUE: 0.20,
    Band.GREEN: 0.25,
    Band.RED: 0.30,
    Band.NIR: 0.35,
    Band.SWIR16: 0.45,
    Band.SWIR22: 0.40,
}
WATER = {
    Band.BLUE: 0.08,
    Band.GREEN: 0.10,
    Band.RED: 0.07,
    Band.NIR: 0.04,
    Band.SWIR16: 0.02,
    Band.SWIR22: 0.01,
}
PALMS = {
    Band.BLUE: 0.05,
    Band.GREEN: 0.08,
    Band.RED: 0.06,
    Band.NIR: 0.35,
    Band.SWIR16: 0.20,
    Band.SWIR22: 0.10,
}
CONCRETE = {
    Band.BLUE: 0.28,
    Band.GREEN: 0.30,
    Band.RED: 0.32,
    Band.NIR: 0.30,
    Band.SWIR16: 0.52,
    Band.SWIR22: 0.48,
}
DUNE_SAND = {
    Band.BLUE: 0.26,
    Band.GREEN: 0.34,
    Band.RED: 0.50,
    Band.NIR: 0.44,
    Band.SWIR16: 0.64,
    Band.SWIR22: 0.60,
}
FRESH_SOIL = {
    Band.BLUE: 0.14,
    Band.GREEN: 0.18,
    Band.RED: 0.22,
    Band.NIR: 0.26,
    Band.SWIR16: 0.32,
    Band.SWIR22: 0.30,
}
RULES = ChangeRules(minimum_baseline_observations=3, minimum_recent_observations=1)


def square(half_m: float) -> list[LatLon]:
    d_lat = half_m / 111_195
    d_lon = half_m / (111_195 * np.cos(np.radians(CENTRE.lat)))
    return [
        LatLon(CENTRE.lat + d_lat, CENTRE.lon - d_lon),
        LatLon(CENTRE.lat + d_lat, CENTRE.lon + d_lon),
        LatLon(CENTRE.lat - d_lat, CENTRE.lon + d_lon),
        LatLon(CENTRE.lat - d_lat, CENTRE.lon - d_lon),
    ]


def scene(day: int, surface=DESERT, patch=None, patch_surface=None, cloud=None) -> Scene:
    bands = {band: np.full((40, 40), value, np.float32) for band, value in surface.items()}
    if patch is not None:
        for band, value in patch_surface.items():
            bands[band][patch] = value
    clear = np.ones((40, 40), bool)
    if cloud is not None:
        clear[cloud] = False
    return Scene(date(2026, 10, day), bands, clear)


SITE_ZONES = zones(square(100), CENTRE, WINDOW, buffer_m=60)
CORE = (slice(17, 23), slice(17, 23))


def test_local_xy_measures_metres_east_and_north():
    east, north = local_xy([LatLon(CENTRE.lat + 0.001, CENTRE.lon + 0.001)], CENTRE)[0]
    assert north == pytest.approx(111.2, abs=0.2)
    assert east == pytest.approx(101.0, abs=0.5)


def test_zones_split_the_site_from_its_surroundings():
    assert SITE_ZONES.inside.sum() == 400
    assert not (SITE_ZONES.inside & SITE_ZONES.ring).any()
    assert 400 < SITE_ZONES.ring.sum() < 1200
    assert SITE_ZONES.inside[20, 20] and not SITE_ZONES.inside[0, 0] and not SITE_ZONES.ring[0, 0]


def test_composite_ignores_cloudy_pixels():
    hazy = scene(1, surface={b: v + 0.4 for b, v in DESERT.items()}, cloud=(slice(0, 40), slice(0, 40)))
    composite = median_composite([scene(2), scene(3), hazy])
    assert composite.bands[Band.RED][5, 5] == pytest.approx(0.30)
    assert composite.observations[5, 5] == 2
    assert composite.scene_dates == (date(2026, 10, 1), date(2026, 10, 2), date(2026, 10, 3))


def test_pixels_never_seen_clear_stay_missing():
    composite = median_composite([scene(1, cloud=(slice(0, 2), slice(0, 2)))])
    assert np.isnan(composite.bands[Band.NIR][0, 0]) and composite.observations[0, 0] == 0


def test_standing_water_inside_the_site_is_found():
    baseline = median_composite([scene(d) for d in (1, 2, 3, 4)])
    recent = median_composite([scene(20, patch=CORE, patch_surface=WATER)])

    report = detect_changes(baseline, recent, SITE_ZONES, WINDOW, RULES)

    assert report.status is ScreeningStatus.OK
    assert [(s.threat, s.zone, s.changed_pixels, s.area_m2) for s in report.signals] == [
        (Threat.WATER, Zone.INSIDE, 36, 3600.0)
    ]


def test_palms_cleared_next_to_the_site_count_as_vegetation_loss():
    grove = (slice(2, 8), slice(17, 23))
    baseline = median_composite([scene(d, patch=grove, patch_surface=PALMS) for d in (1, 2, 3)])
    recent = median_composite([scene(20)])

    report = detect_changes(baseline, recent, SITE_ZONES, WINDOW, RULES)

    assert [(s.threat, s.zone) for s in report.signals] == [(Threat.VEGETATION_LOSS, Zone.RING)]


def test_an_unchanged_site_has_no_signals():
    baseline = median_composite([scene(d) for d in (1, 2, 3)])
    report = detect_changes(baseline, median_composite([scene(20)]), SITE_ZONES, WINDOW, RULES)
    assert report.status is ScreeningStatus.OK and report.signals == ()
    assert assess(report).level is RiskLevel.STABLE


def test_too_few_clear_looks_means_no_verdict_instead_of_a_false_alarm():
    baseline = median_composite([scene(1), scene(2)])
    recent = median_composite([scene(20, patch=CORE, patch_surface=WATER)])

    report = detect_changes(baseline, recent, SITE_ZONES, WINDOW, RULES)

    assert report.status is ScreeningStatus.INSUFFICIENT_DATA and report.signals == ()
    assert assess(report).level is RiskLevel.UNKNOWN


@pytest.mark.parametrize(
    ("surface", "threat"),
    [(CONCRETE, Threat.CONSTRUCTION), (DUNE_SAND, Threat.SAND), (FRESH_SOIL, Threat.EARTHWORKS)],
)
def test_new_surfaces_inside_the_site_are_told_apart(surface, threat):
    baseline = median_composite([scene(d) for d in (1, 2, 3)])
    recent = median_composite([scene(20, patch=CORE, patch_surface=surface)])

    report = detect_changes(baseline, recent, SITE_ZONES, WINDOW, RULES)

    assert [(s.threat, s.zone, s.changed_pixels) for s in report.signals] == [(threat, Zone.INSIDE, 36)]


def test_change_within_the_usual_spread_of_a_noisy_pixel_is_not_flagged():
    noisy = [scene(d, surface={b: v + 0.03 * (d % 3 - 1) for b, v in DESERT.items()}) for d in range(1, 10)]
    recent = median_composite([scene(20, surface={b: v + 0.03 for b, v in DESERT.items()})])

    assert detect_changes(median_composite(noisy), recent, SITE_ZONES, WINDOW, RULES).signals == ()


def test_a_tiny_change_below_the_noise_floor_is_ignored():
    baseline = median_composite([scene(d) for d in (1, 2, 3)])
    recent = median_composite([scene(20, patch=(slice(20, 21), slice(20, 22)), patch_surface=WATER)])
    assert detect_changes(baseline, recent, SITE_ZONES, WINDOW, RULES).signals == ()


def report_with(*signals: Signal):
    return ChangeReport(ScreeningStatus.OK, 1.0, signals)


def test_risk_weighs_change_inside_the_site_above_change_around_it():
    inside = assess(report_with(Signal(Threat.EARTHWORKS, Zone.INSIDE, 10, 400, 1000.0)))
    around = assess(report_with(Signal(Threat.EARTHWORKS, Zone.RING, 10, 800, 1000.0)))
    assert (inside.score, inside.level) == (50, RiskLevel.MODERATE)
    assert (around.score, around.level) == (25, RiskLevel.WATCH)


def test_risk_is_capped_and_lists_the_heaviest_reason_first():
    risk = assess(
        report_with(
            Signal(Threat.SAND, Zone.RING, 30, 800, 3000.0),
            Signal(Threat.WATER, Zone.INSIDE, 50, 400, 5000.0),
            Signal(Threat.CONSTRUCTION, Zone.RING, 40, 800, 4000.0),
        )
    )
    assert risk.score == 100 and risk.level is RiskLevel.URGENT
    assert [r.threat for r in risk.reasons] == [Threat.WATER, Threat.CONSTRUCTION, Threat.SAND]


@pytest.mark.parametrize(
    ("score", "level"),
    [
        (0, RiskLevel.STABLE),
        (9, RiskLevel.STABLE),
        (10, RiskLevel.WATCH),
        (30, RiskLevel.MODERATE),
        (60, RiskLevel.URGENT),
    ],
)
def test_level_floors(score, level):
    assert level_for(score) is level


def test_world_heritage_sites_come_first_at_equal_risk():
    risk = assess(report_with(Signal(Threat.EARTHWORKS, Zone.INSIDE, 10, 400, 1000.0)))
    assert priority(risk, world_heritage=True) > priority(risk, world_heritage=False)
