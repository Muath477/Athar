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
import { useCallback, useMemo, useRef, useState, useSyncExternalStore } from "react";
import type { Site } from "@/lib/api";
import { placeUrl, type TravelMode } from "@/lib/directions";
import { themeColor } from "@/lib/theme-color";
import { FootprintSketch } from "./footprint-sketch";
import { RouteControls } from "./route-controls";
import { useRouteToSite } from "./use-route-to-site";

const OPENING_RANGE_M = 1500;
const ORBIT_TILT = 65;
const ORBIT_MILLIS = 26000;
const BOUNDARY_HEIGHT_M = 8;

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
  const reducedMotion = usePrefersReducedMotion();
  const route = useRouteToSite(site.location, mode);
  const colors = useMemo(
    () => ({
      fill: themeColor("clay", 0.45),
      stroke: themeColor("sadu"),
      glyph: themeColor("sand"),
      route: themeColor("sadu"),
      origin: themeColor("ink"),
    }),
    [],
  );
  const boundary = useMemo(
    () => site.boundary.map((p) => ({ lat: p.lat, lng: p.lon, altitude: BOUNDARY_HEIGHT_M })),
    [site.boundary],
  );

  const orbit = useCallback(() => {
    const map = mapRef.current?.map3d;
    if (!map?.center) return;
    mapRef.current?.flyCameraAround({
      camera: { center: map.center, range: map.range ?? 400, tilt: ORBIT_TILT, heading: map.heading ?? 0 },
      durationMillis: ORBIT_MILLIS,
      repeatCount: 1,
    });
  }, []);

  const stop = useCallback(() => mapRef.current?.stopCameraAnimation(), []);

  function orbitOnFirstRest(event: Map3DSteadyChangeEvent) {
    if (!event.detail.isSteady || orbitedOnce.current || reducedMotion) return;
    orbitedOnce.current = true;
    orbit();
  }

  return (
    <div className="relative size-full bg-ink">
      <Map3D
        ref={mapRef}
        mode={MapMode.SATELLITE}
        defaultCenter={{ lat: site.location.lat, lng: site.location.lon, altitude: 0 }}
        defaultRange={OPENING_RANGE_M}
        defaultTilt={55}
        defaultHeading={0}
        gestureHandling={GestureHandling.COOPERATIVE}
        onSteadyChange={orbitOnFirstRest}
        onError={onFail}
        className="size-full"
      >
        <Polygon3D
          outerCoordinates={boundary}
          altitudeMode={AltitudeMode.RELATIVE_TO_GROUND}
          extruded
          drawsOccludedSegments
          autofitsCamera={route.state.status !== "ready"}
          fillColor={colors.fill}
          strokeColor={colors.stroke}
          strokeWidth={3}
        />
        <Marker3D
          position={{ lat: site.location.lat, lng: site.location.lon, altitude: 40 }}
          altitudeMode={AltitudeMode.RELATIVE_TO_GROUND}
          extruded
          title={site.name_ar}
        >
          <Pin background={colors.stroke} borderColor={colors.glyph} glyphColor={colors.glyph} />
        </Marker3D>
        {route.state.status === "ready" && (
          <>
            <Polyline3D
              path={route.state.path}
              altitudeMode={AltitudeMode.CLAMP_TO_GROUND}
              drawsOccludedSegments
              autofitsCamera
              strokeColor={colors.route}
              strokeWidth={8}
            />
            <Marker3D position={{ ...route.state.origin, altitude: 0 }} altitudeMode={AltitudeMode.CLAMP_TO_GROUND} title="موقعك">
              <Pin background={colors.origin} borderColor={colors.glyph} glyphColor={colors.glyph} scale={0.8} />
            </Marker3D>
          </>
        )}
      </Map3D>

      <div className="pointer-events-none absolute inset-x-3 top-3 flex flex-wrap gap-2">
        <button onClick={orbit} className="pointer-events-auto min-h-11 rounded-full bg-sand/95 px-4 text-sm shadow">
          دُر حول المكان
        </button>
        <button onClick={stop} className="pointer-events-auto min-h-11 rounded-full bg-sand/95 px-4 text-sm shadow">
          أوقف الحركة
        </button>
      </div>

      <RouteControls route={route} />
    </div>
  );
}

function LoadPrompt({ site, onLoad }: { site: Site; onLoad: () => void }) {
  return (
    <div className="flex size-full flex-col items-center justify-center gap-4 bg-white/60 p-6 text-center">
      <FootprintSketch boundary={site.boundary} />
      <p className="max-w-sm leading-relaxed">
        شاهد {site.name_ar} مجسّمًا على خريطة Google، ودُر حوله من كل الجهات قبل أن تصل.
      </p>
      <button onClick={onLoad} className="min-h-11 rounded-full bg-sadu px-6 text-lg font-bold text-sand shadow">
        اعرض المجسّم
      </button>
      <p className="max-w-sm text-xs text-mud">تُحمَّل الخريطة من Google عند الضغط فقط، فلا نستهلك بياناتك قبل أن تطلبها.</p>
    </div>
  );
}

function MapUnavailable({ site }: { site: Site }) {
  return (
    <div className="flex size-full flex-col items-center justify-center gap-3 bg-white/60 p-6 text-center">
      <FootprintSketch boundary={site.boundary} />
      <p className="max-w-sm">تعذّر تحميل خريطة Google الآن. شاهد نموذج الواجهات، أو افتح المكان في Google Maps.</p>
      <a href={placeUrl(site.location)} target="_blank" rel="noreferrer" className="min-h-11 content-center rounded-full border border-ink px-5">
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
