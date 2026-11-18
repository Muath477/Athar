import type { Metadata, Viewport } from "next";
import localFont from "next/font/local";
import Link from "next/link";
import { AtharWordmark } from "@/components/brand/athar-mark";
import { Providers } from "@/components/providers";
import { SiteNav } from "./_components/site-nav";
import "./globals.css";

const scheherazade = localFont({
  src: [
    { path: "./fonts/scheherazade-new-arabic-400-normal.woff2", weight: "400", style: "normal" },
    { path: "./fonts/scheherazade-new-arabic-700-normal.woff2", weight: "700", style: "normal" },
  ],
  variable: "--font-scheherazade",
  display: "swap",
  fallback: ["Noto Naskh Arabic", "Geeza Pro", "serif"],
});

const cormorant = localFont({
  src: [
    { path: "./fonts/cormorant-garamond-latin-500-normal.woff2", weight: "500", style: "normal" },
    { path: "./fonts/cormorant-garamond-latin-700-normal.woff2", weight: "700", style: "normal" },
  ],
  variable: "--font-cormorant",
  display: "swap",
  fallback: ["Georgia", "serif"],
});

export const metadata: Metadata = {
  title: "أثر",
  description: "صوّر واجهة المبنى التراثي، واسمع حكايته الموثقة، وساعد في حمايته.",
  applicationName: "أثر",
};

export const viewport: Viewport = {
  themeColor: "#f5ecd7",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ar" dir="rtl" className={`${scheherazade.variable} ${cormorant.variable}`}>
      <body className="flex min-h-dvh flex-col">
        <Providers>
          <header className="bg-white">
            <div className="mx-auto flex w-full max-w-5xl items-center justify-between gap-4 px-4 py-2">
              <Link href="/" aria-label="أثر، الصفحة الرئيسية" className="inline-flex min-h-11 items-center text-ink">
                <AtharWordmark />
              </Link>
              <SiteNav />
            </div>
            <div className="jadwal" aria-hidden />
          </header>
          <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col px-4 pt-4 pb-10">{children}</main>
        </Providers>
      </body>
    </html>
  );
}
