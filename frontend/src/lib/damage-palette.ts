export const damageColor: Record<string, string> = {
  crack: "#c0392b",
  plaster_loss: "#e67e22",
  moisture: "#2471a3",
  basal_erosion: "#7d3c98",
  surface_erosion: "#b7950b",
  partial_collapse: "#1c1c1c",
  graffiti: "#138d75",
};

export const severityOpacity: Record<string, number> = { watch: 0.3, moderate: 0.5, urgent: 0.72 };

export function colorFor(damageType: string): string {
  return damageColor[damageType] ?? "#555555";
}
