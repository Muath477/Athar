import pytest

from sadu.modules.sites.domain.geometry import PIN_OFFSET_M, FacadePlane, heading_score

# A 10 m wide, 4 m high wall in the X-Y plane, seen from +Z.
SOUTH_WALL = [(0.0, 0.0, 0.0), (10.0, 0.0, 0.0), (10.0, 4.0, 0.0), (0.0, 4.0, 0.0)]


def test_plane_dimensions_and_outward_normal() -> None:
    plane = FacadePlane.from_corners(SOUTH_WALL)
    assert plane.width_m == pytest.approx(10.0)
    assert plane.height_m == pytest.approx(4.0)
    assert plane.normal == pytest.approx((0.0, 0.0, 1.0))


@pytest.mark.parametrize(
    ("uv", "expected"),
    [
        ((0.0, 0.0), (0.0, 0.0, PIN_OFFSET_M)),
        ((0.5, 0.5), (5.0, 2.0, PIN_OFFSET_M)),
        ((1.0, 1.0), (10.0, 4.0, PIN_OFFSET_M)),
        ((1.7, -0.2), (10.0, 0.0, PIN_OFFSET_M)),
    ],
)
def test_uv_to_xyz(uv: tuple[float, float], expected: tuple[float, float, float]) -> None:
    assert FacadePlane.from_corners(SOUTH_WALL).uv_to_xyz(*uv) == pytest.approx(expected)


def test_rejects_degenerate_corners() -> None:
    with pytest.raises(ValueError, match="coincide"):
        FacadePlane.from_corners([(0.0, 0.0, 0.0)] * 4)


def test_rejects_wrong_corner_count() -> None:
    with pytest.raises(ValueError, match="4 corners"):
        FacadePlane.from_corners(SOUTH_WALL[:3])


@pytest.mark.parametrize(
    ("camera_heading", "outward_azimuth", "expected"),
    [(0.0, 180.0, 1.0), (180.0, 180.0, -1.0), (90.0, 180.0, 0.0), (350.0, 170.0, 1.0)],
)
def test_heading_score(camera_heading: float, outward_azimuth: float, expected: float) -> None:
    assert heading_score(camera_heading, outward_azimuth) == pytest.approx(expected, abs=1e-9)
