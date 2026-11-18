from sadu.shared.vocabulary import DamageType, Severity

DAMAGE_COLORS: dict[DamageType, str] = {
    DamageType.PLASTER_LOSS: "#2f5ea8",
    DamageType.CRACK: "#b0357c",
    DamageType.BASAL_EROSION: "#e07b22",
    DamageType.RAIN_GULLY: "#1f7f78",
    DamageType.SALT_EFFLORESCENCE: "#f4f1ec",
    DamageType.CAVITY: "#1b1b24",
    DamageType.WALL_HEAD: "#a04000",
    DamageType.CEMENT_REPAIR: "#6c7a89",
    DamageType.MOISTURE: "#5dade2",
    DamageType.SURFACE_EROSION: "#b7950b",
    DamageType.PARTIAL_COLLAPSE: "#6e2c00",
    DamageType.GRAFFITI: "#8e44ad",
}

SEVERITY_OPACITY: dict[Severity, float] = {
    Severity.WATCH: 0.3,
    Severity.MODERATE: 0.5,
    Severity.URGENT: 0.72,
}


def bgr(hex_color: str) -> tuple[int, int, int]:
    value = hex_color.removeprefix("#")
    red, green, blue = (int(value[i : i + 2], 16) for i in (0, 2, 4))
    return blue, green, red
