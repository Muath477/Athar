import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "أثر",
    short_name: "أثر",
    description: "صوّر واجهة المبنى التراثي واسمع حكايته الموثقة.",
    lang: "ar",
    dir: "rtl",
    start_url: "/",
    display: "standalone",
    background_color: "#f5ecd7",
    theme_color: "#f5ecd7",
    icons: [{ src: "/icon.svg", sizes: "any", type: "image/svg+xml", purpose: "any" }],
  };
}
