export type Position = { lat: number; lon: number; accuracy: number };

export function currentPosition(timeoutMs = 10000): Promise<Position> {
  return new Promise((resolve, reject) => {
    if (!("geolocation" in navigator)) {
      reject(new Error("geolocation_unavailable"));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (p) => resolve({ lat: p.coords.latitude, lon: p.coords.longitude, accuracy: p.coords.accuracy }),
      reject,
      { enableHighAccuracy: true, timeout: timeoutMs, maximumAge: 30000 },
    );
  });
}

export type Heading = { degrees: number; accuracy: number | null };

type CompassEvent = DeviceOrientationEvent & { webkitCompassHeading?: number; webkitCompassAccuracy?: number };
type OrientationPermission = { requestPermission?: () => Promise<"granted" | "denied"> };

/** Starts listening to the compass; returns a function that stops it. iOS asks the user first. */
export async function watchHeading(onHeading: (heading: Heading) => void): Promise<() => void> {
  const permission = (DeviceOrientationEvent as unknown as OrientationPermission).requestPermission;
  if (permission && (await permission()) !== "granted") throw new Error("heading_denied");

  const handler = (event: Event) => {
    const e = event as CompassEvent;
    if (typeof e.webkitCompassHeading === "number") {
      onHeading({ degrees: e.webkitCompassHeading, accuracy: e.webkitCompassAccuracy ?? null });
    } else if (e.absolute && typeof e.alpha === "number") {
      // alpha grows counter-clockwise from north; compass headings grow clockwise.
      onHeading({ degrees: (360 - e.alpha) % 360, accuracy: null });
    }
  };
  const eventName = "ondeviceorientationabsolute" in window ? "deviceorientationabsolute" : "deviceorientation";
  window.addEventListener(eventName, handler);
  return () => window.removeEventListener(eventName, handler);
}
