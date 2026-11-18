from sadu.shared.vocabulary import DamageType, Severity

DAMAGE_COLORS: dict[DamageType, str] = {
    DamageType.CRACK: "#c0392b",
    DamageType.PLASTER_LOSS: "#e67e22",
    DamageType.MOISTURE: "#2471a3",
    DamageType.BASAL_EROSION: "#7d3c98",
    DamageType.SURFACE_EROSION: "#b7950b",
    DamageType.PARTIAL_COLLAPSE: "#1c1c1c",
    DamageType.GRAFFITI: "#138d75",
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
