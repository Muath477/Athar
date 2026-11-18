import { describe, expect, it } from "vitest";
import { directionsUrl, distanceAr, durationAr, placeUrl } from "./directions";

describe("directions", () => {
  it("builds a Google Maps directions link that needs no key", () => {
    const url = new URL(directionsUrl({ lat: 24.734133, lon: 46.572467 }, "walking"));
    expect(url.origin + url.pathname).toBe("https://www.google.com/maps/dir/");
    expect(Object.fromEntries(url.searchParams)).toEqual({
      api: "1",
      destination: "24.734133,46.572467",
      travelmode: "walking",
    });
  });

  it("builds a place link", () => {
    expect(new URL(placeUrl({ lat: 24.7, lon: 46.5 })).searchParams.get("query")).toBe("24.7,46.5");
  });

  it("rounds short distances to ten metres and long ones to a tenth of a kilometre", () => {
    expect(distanceAr(347)).toBe("٣٥٠ م");
    expect(distanceAr(2011)).toBe("٢ كم");
    expect(distanceAr(2560)).toBe("٢٫٦ كم");
  });

  it("never shows zero minutes and splits hours", () => {
    expect(durationAr(10_000)).toBe("١ دقيقة");
    expect(durationAr(26 * 60_000)).toBe("٢٦ دقيقة");
    expect(durationAr(120 * 60_000)).toBe("٢ ساعة");
    expect(durationAr(95 * 60_000)).toBe("١ ساعة و٣٥ دقيقة");
  });
});
