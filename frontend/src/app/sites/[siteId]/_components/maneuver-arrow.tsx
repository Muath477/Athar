const TURN_DEGREES: Record<string, number> = {
  TURN_SLIGHT_LEFT: -45,
  TURN_LEFT: -90,
  TURN_SHARP_LEFT: -135,
  TURN_SLIGHT_RIGHT: 45,
  TURN_RIGHT: 90,
  TURN_SHARP_RIGHT: 135,
  UTURN_LEFT: 180,
  UTURN_RIGHT: 180,
  RAMP_LEFT: -30,
  RAMP_RIGHT: 30,
  FORK_LEFT: -30,
  FORK_RIGHT: 30,
  ROUNDABOUT_LEFT: -90,
  ROUNDABOUT_RIGHT: 90,
};

export function ManeuverArrow({ maneuver, className = "size-6" }: { maneuver: string | null; className?: string }) {
  if (maneuver === "DESTINATION") {
    return (
      <svg viewBox="0 0 24 24" className={className} aria-hidden>
        <circle cx="12" cy="12" r="5" className="fill-current" />
        <circle cx="12" cy="12" r="9" className="fill-none stroke-current" strokeWidth={2} />
      </svg>
    );
  }
  const degrees = TURN_DEGREES[maneuver ?? ""] ?? 0;
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden>
      <g transform={`rotate(${degrees} 12 12)`}>
        <path d="M12 3 L18 10 H14 V21 H10 V10 H6 Z" className="fill-current" />
      </g>
    </svg>
  );
}
