import type { Metadata, Viewport } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "سدو",
  description: "صوّر واجهة المبنى التراثي، واسمع حكايته الموثقة، وساعد في حمايته.",
  applicationName: "سدو",
};

export const viewport: Viewport = {
  themeColor: "#8f1f1a",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ar" dir="rtl">
      <body className="flex min-h-dvh flex-col">
        <div className="sadu-band" aria-hidden />
        <header className="flex items-center justify-between px-4 py-3">
          <Link href="/" className="text-2xl font-bold text-sadu">
            سدو
          </Link>
          <nav className="flex gap-4 text-sm">
            <Link href="/passport">جوازي</Link>
            <Link href="/dashboard">لوحة المتابعة</Link>
          </nav>
        </header>
        <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col px-4 pb-10">{children}</main>
      </body>
    </html>
  );
}
