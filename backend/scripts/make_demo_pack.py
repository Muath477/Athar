"""Generate the synthetic demo region pack: a 10 m x 8 m x 6 m mud-brick box with four facades.

Everything here is synthetic. Real sites replace this pack with surveyed corners, real
baseline photos and reviewed sources (see region-packs/README.md).
Run from backend/: uv run python -m scripts.make_demo_pack
"""

import json
from pathlib import Path

import cv2
from tests.synthetic import mud_wall, photograph, unrelated_scene, with_crack, with_soft_shadow

PACK_DIR = Path(__file__).resolve().parents[2] / "region-packs" / "demo"
SLUG = "demo-house"
HEIGHT_M = 6.0

# (code, Arabic name, English name, outward azimuth, corners BL, BR, TR, TL at ground level, seed)
FACADES = [
    ("north", "الواجهة الشمالية", "North facade", 0.0, (5, -4), (-5, -4), 11),
    ("east", "الواجهة الشرقية", "East facade", 90.0, (5, 4), (5, -4), 12),
    ("south", "الواجهة الجنوبية", "South facade", 180.0, (-5, 4), (5, 4), 13),
    ("west", "الواجهة الغربية", "West facade", 270.0, (-5, -4), (-5, 4), 14),
]
CAMERA_DISTANCE_M = 14.0


def facade_entry(code: str, names: tuple[str, str], azimuth: float, left: tuple, right: tuple) -> dict:
    (lx, lz), (rx, rz) = left, right
    corners = [[lx, 0, lz], [rx, 0, rz], [rx, HEIGHT_M, rz], [lx, HEIGHT_M, lz]]
    center = [(lx + rx) / 2, HEIGHT_M / 2, (lz + rz) / 2]
    # Outward direction in model space: x east, -z north.
    outward = {0.0: (0, -1), 90.0: (1, 0), 180.0: (0, 1), 270.0: (-1, 0)}[azimuth]
    position = [center[0] + outward[0] * CAMERA_DISTANCE_M, 4.0, center[2] + outward[1] * CAMERA_DISTANCE_M]
    return {
        "code": code,
        "name_ar": names[0],
        "name_en": names[1],
        "outward_azimuth_deg": azimuth,
        "corners": corners,
        "default_camera": {"position": position, "target": center},
    }


def main() -> None:
    (PACK_DIR / "baselines").mkdir(parents=True, exist_ok=True)
    (PACK_DIR / "test-photos").mkdir(exist_ok=True)

    facades, baselines = [], []
    for code, name_ar, name_en, azimuth, left, right, seed in FACADES:
        facades.append(facade_entry(code, (name_ar, name_en), azimuth, left, right))
        wall = mud_wall(seed)
        height, width = wall.shape[:2]
        file = f"baselines/{code}.jpg"
        cv2.imwrite(str(PACK_DIR / file), wall, [cv2.IMWRITE_JPEG_QUALITY, 90])
        baselines.append(
            {
                "facade_code": code,
                "file": file,
                "corners_px": [[0, height], [width, height], [width, 0], [0, 0]],
            }
        )

    north = mud_wall(11)
    photos = {
        "north-unchanged.jpg": photograph(north, brightness=1.1),
        "north-crack.jpg": photograph(with_crack(north), brightness=0.95),
        "north-shadow.jpg": photograph(with_soft_shadow(north)),
        "not-a-facade.jpg": unrelated_scene(),
    }
    for name, image in photos.items():
        cv2.imwrite(str(PACK_DIR / "test-photos" / name), image, [cv2.IMWRITE_JPEG_QUALITY, 90])

    write_json("facade_map.json", {"site_slug": SLUG, "units": "meters", "up_axis": "Y", "facades": facades})
    write_json(
        "pack.json",
        {
            "code": "demo",
            "name_ar": "حزمة تجريبية",
            "name_en": "Demo pack",
            "version": "1",
            "sites": [
                {
                    "slug": SLUG,
                    "name_ar": "بيت طيني تجريبي",
                    "name_en": "Demo mud-brick house",
                    "building_type": "mud_brick_house",
                    # Placeholder point in Riyadh for the demo; not a heritage site.
                    "location": [46.6753, 24.7136],
                    "boundary": [
                        [46.6750, 24.7133],
                        [46.6756, 24.7133],
                        [46.6756, 24.7139],
                        [46.6750, 24.7139],
                        [46.6750, 24.7133],
                    ],
                    "facade_map_file": "facade_map.json",
                    "baselines": baselines,
                    "sources_file": "sources.json",
                }
            ],
        },
    )


def write_json(name: str, payload: dict) -> None:
    (PACK_DIR / name).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
