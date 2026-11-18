export type ThemeToken = "sand" | "clay" | "mud" | "ink" | "sadu";

export function themeColor(token: ThemeToken, opacity = 1): string {
  const declared = getComputedStyle(document.documentElement).getPropertyValue(`--color-${token}`).trim();
  if (opacity >= 1 || !/^#[0-9a-f]{6}$/i.test(declared)) return declared;
  const alpha = Math.round(Math.min(Math.max(opacity, 0), 1) * 255)
    .toString(16)
    .padStart(2, "0");
  return `${declared}${alpha}`;
}
