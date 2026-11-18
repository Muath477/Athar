"use client";

import { useMapsLibrary } from "@vis.gl/react-google-maps";
import { useCallback, useState } from "react";
import type { LatLon } from "@/lib/api";
import { googleTravelMode, type TravelMode } from "@/lib/directions";
import { currentPosition } from "@/lib/geo";
import type { Point } from "@/lib/route-geometry";

export type RouteStep = {
  instruction: string;
  maneuver: string | null;
  distanceMeters: number;
  start: Point;
  path: Point[];
};

export type PlannedRoute = {
  mode: TravelMode;
  origin: Point;
  path: Point[];
  steps: RouteStep[];
  distanceMeters: number;
  durationMillis: number;
};

export type RouteState =
  | { status: "idle" | "locating" | "routing" | "no_location" | "no_route" | "failed" }
  | ({ status: "ready" } & PlannedRoute);

export function useRouteToSite(destination: LatLon, mode: TravelMode) {
  const routes = useMapsLibrary("routes");
  const [state, setState] = useState<RouteState>({ status: "idle" });

  const find = useCallback(async () => {
    if (!routes) return;
    setState({ status: "locating" });
    let origin: Point;
    try {
      const position = await currentPosition();
      origin = { lat: position.lat, lng: position.lon };
    } catch {
      setState({ status: "no_location" });
      return;
    }

    setState({ status: "routing" });
    try {
      const { routes: found } = await routes.Route.computeRoutes({
        origin,
        destination: { lat: destination.lat, lng: destination.lon },
        travelMode: googleTravelMode(mode),
        fields: ["path", "distanceMeters", "durationMillis", "legs"],
        language: "ar",
        region: "SA",
      });
      const best = found?.[0];
      if (!best?.path?.length) {
        setState({ status: "no_route" });
        return;
      }
      setState({
        status: "ready",
        mode,
        origin,
        path: best.path.map(toPoint),
        steps: (best.legs ?? []).flatMap((leg) => leg.steps.map(toStep)),
        distanceMeters: best.distanceMeters ?? 0,
        durationMillis: best.durationMillis ?? 0,
      });
    } catch {
      setState({ status: "failed" });
    }
  }, [routes, destination.lat, destination.lon, mode]);

  const clear = useCallback(() => setState({ status: "idle" }), []);

  return { state, find, clear, available: routes !== null };
}

function toPoint(point: google.maps.LatLngAltitude): Point {
  return { lat: point.lat, lng: point.lng };
}

function toStep(step: google.maps.routes.RouteLegStep): RouteStep {
  const path = step.path.map(toPoint);
  return {
    instruction: step.instructions?.trim() || "تابع على الطريق",
    maneuver: step.maneuver,
    distanceMeters: step.distanceMeters,
    start: step.startLocation ? toPoint(step.startLocation) : path[0],
    path,
  };
}
