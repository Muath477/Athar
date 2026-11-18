"use client";

import Link from "next/link";
import { Button, buttonVariants } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { distanceAr, durationAr, travelModeAr } from "@/lib/directions";
import type { RouteProgress } from "./route-progress";
import { RouteSteps } from "./route-steps";
import type { RouteState, useRouteToSite } from "./use-route-to-site";

const PROBLEM_AR: Partial<Record<RouteState["status"], string>> = {
  no_location: "لم نصل إلى موقعك. اسمح بالموقع من إعدادات المتصفح، أو افتح الاتجاهات في Google Maps.",
  no_route: "لم يجد Google طريقًا بهذه الطريقة. جرّب طريقة وصول أخرى.",
  failed: "تعذّر حساب الطريق الآن. افتح الاتجاهات في Google Maps.",
};

const BUSY_AR: Partial<Record<RouteState["status"], string>> = {
  locating: "نحدد موقعك…",
  routing: "نحسب الطريق…",
};

type Props = {
  route: ReturnType<typeof useRouteToSite>;
  siteName: string;
  tracking: boolean;
  trackingDenied: boolean;
  progress: RouteProgress | null;
  following: boolean;
  canPreview: boolean;
  onPreview: () => void;
  onToggleTracking: () => void;
  onToggleFollowing: () => void;
  onFocusStep: (index: number) => void;
};

export function RoutePanel(props: Props) {
  const { route } = props;
  const { state } = route;

  if (state.status !== "ready") {
    const busy = BUSY_AR[state.status];
    return (
      <section className="flex flex-col gap-2 rounded-sm border border-line bg-white p-4" aria-label="الطريق على الخريطة">
        <Button
          type="button"
          variant="outline"
          onClick={route.find}
          disabled={!route.available || Boolean(busy)}
          aria-busy={Boolean(busy)}
          className="self-start"
        >
          {busy ?? "ارسم طريقي من موقعي"}
        </Button>
        <p className="text-xs text-mud">نطلب موقعك ونرسله إلى Google لحساب الطريق فقط، ولا نحفظه عندنا.</p>
        <p aria-live="polite" className="text-sm empty:hidden">
          {PROBLEM_AR[state.status] ?? ""}
        </p>
      </section>
    );
  }

  return (
    <section className="flex flex-col gap-3 rounded-sm border border-line bg-white p-4" aria-label="الطريق على الخريطة">
      <p className="text-lg font-bold tabular-nums">
        {props.progress
          ? `باقي ${distanceAr(props.progress.remainingMeters)}`
          : `${distanceAr(state.distanceMeters)} · ${durationAr(state.durationMillis)} ${travelModeAr[state.mode]}`}
      </p>

      <TrackingNotice {...props} />

      <div className="flex flex-wrap gap-2">
        <Button type="button" onClick={props.onToggleTracking}>
          {props.tracking ? "أوقف التتبع" : "ابدأ التتبع"}
        </Button>
        {props.canPreview && !props.tracking && (
          <Button type="button" variant="outline" onClick={props.onPreview}>
            شاهد الطريق قبل أن تمشي
          </Button>
        )}
        {props.tracking && (
          <div className="flex min-h-11 items-center gap-2 px-2">
            <Checkbox id="route-follow" checked={props.following} onCheckedChange={props.onToggleFollowing} />
            <Label htmlFor="route-follow" className="text-ink">
              الكاميرا تتبعني
            </Label>
          </div>
        )}
        <Button type="button" variant="ghost" onClick={route.clear} className="underline underline-offset-4">
          امسح الطريق
        </Button>
      </div>

      <RouteSteps
        steps={state.steps}
        currentIndex={props.progress?.stepIndex ?? null}
        onFocusStep={props.onFocusStep}
      />
    </section>
  );
}

function TrackingNotice({ route, siteName, tracking, trackingDenied, progress }: Props) {
  if (!tracking) return null;
  if (trackingDenied) {
    return <p className="text-sm">لا نستطيع متابعة موقعك. اسمح بالموقع من إعدادات المتصفح ثم ابدأ التتبع من جديد.</p>;
  }
  if (!progress) return <p className="text-sm">ننتظر موقعك…</p>;
  if (progress.arrived) {
    return (
      <div className="flex flex-col gap-2 rounded-sm border border-line bg-sand p-3">
        <p className="font-bold">وصلت إلى {siteName}.</p>
        <p className="text-sm">صوّر واجهته الآن، فصورتك تساعد في متابعة حالته.</p>
        <Link href="/capture" className={buttonVariants({ className: "self-start" })}>
          صوّر الواجهة
        </Link>
      </div>
    );
  }
  if (progress.offRoute) {
    return (
      <div role="alert" className="flex flex-wrap items-center gap-2 rounded-sm border border-moderate bg-moderate/10 p-3 text-sm">
        <p className="flex-1">يبدو أنك ابتعدت عن الطريق.</p>
        <Button type="button" variant="outline" size="sm" onClick={route.find}>
          أعد حساب الطريق
        </Button>
      </div>
    );
  }
  return null;
}
