export const damageColor: Record<string, string> = {
  plaster_loss: "#2f5ea8",
  crack: "#b0357c",
  basal_erosion: "#e07b22",
  rain_gully: "#1f7f78",
  salt_efflorescence: "#f4f1ec",
  cavity: "#1b1b24",
  wall_head: "#a04000",
  cement_repair: "#6c7a89",
  moisture: "#5dade2",
  surface_erosion: "#b7950b",
  partial_collapse: "#6e2c00",
  graffiti: "#8e44ad",
};

export const severityOpacity: Record<string, number> = { watch: 0.3, moderate: 0.5, urgent: 0.72 };

export function colorFor(damageType: string): string {
  return damageColor[damageType] ?? "#555555";
}
