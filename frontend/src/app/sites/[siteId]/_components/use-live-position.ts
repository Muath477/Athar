"use client";

import { useEffect, useState } from "react";
import type { Point } from "@/lib/route-geometry";

export function useLivePosition(enabled: boolean) {
  const [position, setPosition] = useState<Point | null>(null);
  const [denied, setDenied] = useState(false);

  useEffect(() => {
    if (!enabled || !("geolocation" in navigator)) return;
    const watchId = navigator.geolocation.watchPosition(
      (p) => {
        setDenied(false);
        setPosition({ lat: p.coords.latitude, lng: p.coords.longitude });
      },
      (error) => {
        if (error.code === error.PERMISSION_DENIED) setDenied(true);
      },
      { enableHighAccuracy: true, maximumAge: 5000, timeout: 20000 },
    );
    return () => navigator.geolocation.clearWatch(watchId);
  }, [enabled]);

  return { position: enabled ? position : null, denied: enabled && denied };
}
