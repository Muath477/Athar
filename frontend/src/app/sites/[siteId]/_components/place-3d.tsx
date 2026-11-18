"use client";

import { AltitudeMode, APIProvider, Pin } from "@vis.gl/react-google-maps";
import {
  GestureHandling,
  Map3D,
  type Map3DRef,
  type Map3DSteadyChangeEvent,
  MapMode,
  Marker3D,
  Polygon3D,
  Polyline3D,
} from "@vis.gl/react-google-maps/3d";
import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import { Button, buttonVariants } from "@/components/ui/button";
import type { Site } from "@/lib/api";
import { placeUrl, type TravelMode } from "@/lib/directions";
import { bearingDegrees, metersBetween, type Point, sampleAlong } from "@/lib/route-geometry";
import { themeColor } from "@/lib/theme-color";
import { FootprintSketch } from "./footprint-sketch";
import { NextTurn } from "./next-turn";
import { RoutePanel } from "./route-panel";
import { routeProgress } from "./route-progress";
import { useLivePosition } from "./use-live-position";
import { type PlannedRoute, useRouteToSite } from "./use-route-to-site";
import { VIEWPORT_CLASS } from "./viewport";

const OPENING_RANGE_M = 1500;
const ORBIT_TILT = 65;
const ORBIT_MILLIS = 26000;
const BOUNDARY_HEIGHT_M = 8;
const PREVIEW_STOPS = 9;
const PREVIEW_LEG_MILLIS = 2200;
const STREET_RANGE_M = 220;
const FOLLOW_RANGE_M = 160;
const FOLLOW_MIN_MOVE_M = 4;

type Props = { site: Site; apiKey: string; mode: TravelMode };

export function Place3D({ site, apiKey, mode }: Props) {
  const [requested, setRequested] = useState(false);
  const [loadFailed, setLoadFailed] = useState(false);

  if (loadFailed) return <MapUnavailable site={site} />;
  if (!requested) return <LoadPrompt site={site} onLoad={() => setRequested(true)} />;

  return (
    <APIProvider apiKey={apiKey} language="ar" region="SA" onError={() => setLoadFailed(true)}>
      <PlaceScene site={site} mode={mode} onFail={() => setLoadFailed(true)} />
    </APIProvider>
  );
}

function PlaceScene({ site, mode, onFail }: { site: Site; mode: TravelMode; onFail: () => void }) {
  const mapRef = useRef<Map3DRef>(null);
  const orbitedOnce = useRef(false);
  const groundAltitude = useRef(0);
  const cameraQueue = useRef<google.maps.maps3d.CameraOptions[]>([]);
  const lastFollowed = useRef<Point | null>(null);
  const reducedMotion = usePrefersReducedMotion();
  const [tracking, setTracking] = useState(false);
  const [following, setFollowing] = useState(true);

  const destination = useMemo(() => ({ lat: site.location.lat, lng: site.location.lon }), [site.location]);
  const route = useRouteToSite(site.location, mode);
  const live = useLivePosition(tracking && route.state.status === "ready");
  const planned = route.state.status === "ready" ? route.state : null;
  const progress = useMemo(
    () => (planned && live.position ? routeProgress(planned, live.position, destination) : null),
    [planned, live.position, destination],
  );

  const colors = useMemo(
    () => ({
      fill: themeColor("clay", 0.45),
      stroke: themeColor("sadu"),
      light: themeColor("sand"),
      dark: themeColor("ink"),
      travelled: themeColor("ink", 0.45),
    }),
    [],
  );
  const boundary = useMemo(
    () => site.boundary.map((p) => ({ lat: p.lat, lng: p.lon, altitude: BOUNDARY_HEIGHT_M })),
    [site.boundary],
  );

  const flyTo = useCallback(
    (camera: google.maps.maps3d.CameraOptions, durationMillis: number) =>
      mapRef.current?.flyCameraTo({ endCamera: camera, durationMillis: reducedMotion ? 0 : durationMillis }),
    [reducedMotion],
  );

  const streetCamera = useCallback(
    (center: Point, heading: number, range = STREET_RANGE_M): google.maps.maps3d.CameraOptions => ({
      center: { ...center, altitude: groundAltitude.current },
      range,
      tilt: 62,
      heading,
    }),
    [],
  );

  const orbit = useCallback(() => {
    cameraQueue.current = [];
    const map = mapRef.current?.map3d;
    if (!map?.center) return;
    mapRef.current?.flyCameraAround({
      camera: { center: map.center, range: map.range ?? 400, tilt: ORBIT_TILT, heading: map.heading ?? 0 },
      durationMillis: ORBIT_MILLIS,
      repeatCount: 1,
    });
  }, []);

  const stop = useCallback(() => {
    cameraQueue.current = [];
    mapRef.current?.stopCameraAnimation();
  }, []);

  const preview = useCallback(
    (plan: PlannedRoute) => {
      const stops = [...sampleAlong(plan.path, PREVIEW_STOPS), destination];
      cameraQueue.current = stops.slice(0, -1).map((stop, i) => streetCamera(stop, bearingDegrees(stop, stops[i + 1])));
      const first = cameraQueue.current.shift();
      if (first) flyTo(first, PREVIEW_LEG_MILLIS);
    },
    [destination, flyTo, streetCamera],
  );

  const focusStep = useCallback(
    (index: number) => {
      if (!planned) return;
      cameraQueue.current = [];
      const step = planned.steps[index];
      const next = planned.steps[index + 1]?.start ?? destination;
      flyTo(streetCamera(step.start, bearingDegrees(step.start, next)), 1500);
    },
    [planned, destination, flyTo, streetCamera],
  );

  useEffect(() => {
    if (!tracking || !following || !progress || !live.position) return;
    const previous = lastFollowed.current;
    if (previous && metersBetween(previous, live.position) < FOLLOW_MIN_MOVE_M) return;
    lastFollowed.current = live.position;
    cameraQueue.current = [];
    flyTo(streetCamera(live.position, progress.heading, FOLLOW_RANGE_M), 900);
  }, [tracking, following, progress, live.position, flyTo, streetCamera]);

  function handleSteady(event: Map3DSteadyChangeEvent) {
    if (!event.detail.isSteady) return;
    groundAltitude.current = mapRef.current?.map3d?.center?.altitude ?? groundAltitude.current;
    if (orbitedOnce.current) return;
    orbitedOnce.current = true;
    if (!reducedMotion) orbit();
  }

  function continuePreview() {
    const next = cameraQueue.current.shift();
    if (next) flyTo(next, PREVIEW_LEG_MILLIS);
  }

  function toggleTracking() {
    lastFollowed.current = null;
    setTracking((on) => !on);
  }

  return (
    <div className="flex flex-col gap-3">
      <div className={`${VIEWPORT_CLASS} bg-ink`}>
        <Map3D
          ref={mapRef}
          mode={MapMode.SATELLITE}
          defaultCenter={{ ...destination, altitude: 0 }}
          defaultRange={OPENING_RANGE_M}
          defaultTilt={55}
          defaultHeading={0}
          gestureHandling={GestureHandling.COOPERATIVE}
          onSteadyChange={handleSteady}
          onAnimationEnd={continuePreview}
          onError={onFail}
          className="size-full"
        >
          <Polygon3D
            outerCoordinates={boundary}
            altitudeMode={AltitudeMode.RELATIVE_TO_GROUND}
            extruded
            drawsOccludedSegments
            autofitsCamera={!planned}
            fillColor={colors.fill}
            strokeColor={colors.stroke}
            strokeWidth={3}
          />
          <Marker3D
            position={{ ...destination, altitude: 40 }}
            altitudeMode={AltitudeMode.RELATIVE_TO_GROUND}
            extruded
            title={site.name_ar}
          >
            <Pin background={colors.stroke} borderColor={colors.light} glyphColor={colors.light} />
          </Marker3D>
          {planned && (
            <>
              {progress && (
                <Polyline3D
                  path={progress.travelled}
                  altitudeMode={AltitudeMode.CLAMP_TO_GROUND}
                  drawsOccludedSegments
                  strokeColor={colors.travelled}
                  strokeWidth={8}
                />
              )}
              <Polyline3D
                path={progress ? progress.ahead : planned.path}
                altitudeMode={AltitudeMode.CLAMP_TO_GROUND}
                drawsOccludedSegments
                autofitsCamera={!tracking}
                strokeColor={colors.stroke}
                strokeWidth={8}
              />
              <Marker3D
                position={{ ...(live.position ?? planned.origin), altitude: 0 }}
                altitudeMode={AltitudeMode.CLAMP_TO_GROUND}
                title={live.position ? "أنت هنا" : "نقطة البداية"}
              >
                <Pin background={colors.dark} borderColor={colors.light} glyphColor={colors.light} scale={0.8} />
              </Marker3D>
            </>
          )}
        </Map3D>

        <div className="pointer-events-none absolute inset-x-3 top-3 flex flex-wrap gap-2">
          <Button type="button" variant="secondary" size="sm" onClick={orbit} className="pointer-events-auto">
            دُر حول المكان
          </Button>
          <Button type="button" variant="secondary" size="sm" onClick={stop} className="pointer-events-auto">
            أوقف الحركة
          </Button>
        </div>

        {tracking && progress && !progress.arrived && <NextTurn progress={progress} siteName={site.name_ar} />}
      </div>

      <RoutePanel
        route={route}
        siteName={site.name_ar}
        tracking={tracking}
        trackingDenied={live.denied}
        progress={tracking ? progress : null}
        following={following}
        canPreview={!reducedMotion}
        onPreview={() => planned && preview(planned)}
        onToggleTracking={toggleTracking}
        onToggleFollowing={() => setFollowing((on) => !on)}
        onFocusStep={focusStep}
      />
      <p className="text-xs leading-relaxed text-mud">
        إن لم تظهر المباني مجسّمة فالمنطقة خارج تغطية Google للمجسّمات، وتبقى صور الأقمار الصناعية والتضاريس.
      </p>
    </div>
  );
}

function LoadPrompt({ site, onLoad }: { site: Site; onLoad: () => void }) {
  return (
    <div className={`${VIEWPORT_CLASS} flex flex-col items-center justify-center gap-4 bg-white/60 p-6 text-center`}>
      <FootprintSketch boundary={site.boundary} />
      <p className="max-w-sm leading-relaxed">
        شاهد {site.name_ar} مجسّمًا على خريطة Google، ودُر حوله، وارسم طريقك إليه خطوة بخطوة.
      </p>
      <Button type="button" size="lg" onClick={onLoad}>
        اعرض المجسّم
      </Button>
      <p className="max-w-sm text-xs text-mud">تُحمَّل الخريطة من Google عند الضغط فقط، فلا نستهلك بياناتك قبل أن تطلبها.</p>
    </div>
  );
}

function MapUnavailable({ site }: { site: Site }) {
  return (
    <div className={`${VIEWPORT_CLASS} flex flex-col items-center justify-center gap-3 bg-white/60 p-6 text-center`}>
      <FootprintSketch boundary={site.boundary} />
      <p className="max-w-sm">تعذّر تحميل خريطة Google الآن. شاهد نموذج الواجهات، أو افتح المكان في Google Maps.</p>
      <a href={placeUrl(site.location)} target="_blank" rel="noreferrer" className={buttonVariants({ variant: "outline" })}>
        افتح في Google Maps
      </a>
    </div>
  );
}

function usePrefersReducedMotion(): boolean {
  return useSyncExternalStore(
    (notify) => {
      const query = window.matchMedia("(prefers-reduced-motion: reduce)");
      query.addEventListener("change", notify);
      return () => query.removeEventListener("change", notify);
    },
    () => window.matchMedia("(prefers-reduced-motion: reduce)").matches,
    () => true,
  );
}
