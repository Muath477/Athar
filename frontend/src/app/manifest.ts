import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "سدو",
    short_name: "سدو",
    description: "صوّر واجهة المبنى التراثي واسمع حكايته الموثقة.",
    lang: "ar",
    dir: "rtl",
    start_url: "/",
    display: "standalone",
    background_color: "#efe4d2",
    theme_color: "#8f1f1a",
    icons: [{ src: "/icon.svg", sizes: "any", type: "image/svg+xml" }],
  };
}
