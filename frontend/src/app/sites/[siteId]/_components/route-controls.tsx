"use client";

import { distanceAr, durationAr, travelModeAr } from "@/lib/directions";
import type { RouteState, useRouteToSite } from "./use-route-to-site";

type Props = { route: ReturnType<typeof useRouteToSite> };

const STATUS_AR: Partial<Record<RouteState["status"], string>> = {
  locating: "نحدد موقعك…",
  routing: "نحسب الطريق…",
  no_location: "لم نصل إلى موقعك. اسمح بالموقع من إعدادات المتصفح، أو افتح الاتجاهات في Google Maps.",
  no_route: "لم يجد Google طريقًا بهذه الطريقة. جرّب طريقة وصول أخرى.",
  failed: "تعذّر حساب الطريق الآن. افتح الاتجاهات في Google Maps.",
};

export function RouteControls({ route }: Props) {
  const { state } = route;
  const busy = state.status === "locating" || state.status === "routing";

  return (
    <div className="absolute inset-x-3 bottom-3 flex flex-col gap-2 rounded-xl bg-sand/95 p-3 text-sm shadow">
      {state.status === "ready" ? (
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="font-bold tabular-nums">
            {distanceAr(state.distanceMeters)} · {durationAr(state.durationMillis)} {travelModeAr[state.mode]}
          </p>
          <button onClick={route.clear} className="min-h-11 rounded-full border border-ink px-4">
            امسح الطريق
          </button>
        </div>
      ) : (
        <>
          <button
            onClick={route.find}
            disabled={!route.available || busy}
            aria-busy={busy}
            className="min-h-11 self-start rounded-full bg-mud px-5 text-sand disabled:opacity-60"
          >
            {busy ? STATUS_AR[state.status] : "ارسم طريقي من موقعي"}
          </button>
          <p className="text-xs text-mud">نطلب موقعك مرة واحدة ونرسله إلى Google لحساب الطريق فقط، ولا نحفظه عندنا.</p>
        </>
      )}
      <p aria-live="polite" className="empty:hidden">
        {!busy && state.status !== "ready" && state.status !== "idle" ? STATUS_AR[state.status] : ""}
      </p>
    </div>
  );
}
