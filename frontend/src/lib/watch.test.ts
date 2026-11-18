import { describe, expect, it } from "vitest";
import { project } from "@/app/dashboard/watch/_components/region-map";
import { type Scan, type SiteRisk, areaAr, copernicusCredit, strongestSignal } from "@/lib/watch";

function scan(signals: Scan["signals"]): Scan {
  return {
    id: "s",
    site_id: "x",
    created_at: "2026-11-18T08:00:00Z",
    source: "sample",
    is_sample: true,
    status: "ok",
    baseline_start: "2025-10-19",
    baseline_end: "2026-10-19",
    recent_start: "2026-10-19",
    recent_end: "2026-11-18",
    baseline_scenes: 16,
    recent_scenes: 6,
    valid_share: 0.9,
    score: 40,
    level: "moderate",
    signals,
    before_url: null,
    after_url: null,
    change_url: null,
    acknowledged_at: null,
    ground_check_at: null,
    mission_ids: [],
  };
}

function site(lat: number, lon: number): SiteRisk {
  return {
    site_id: `${lat}`,
    slug: "s",
    name_ar: "موقع",
    name_en: "site",
    building_type: "world_heritage",
    location: { lat, lon },
    facades: 0,
    priority: 0,
    scanning: false,
    latest: null,
    failed_attempt: null,
  };
}

describe("watch helpers", () => {
  it("picks the largest change as the headline", () => {
    const strongest = strongestSignal(
      scan([
        { threat: "sand", zone: "ring", changed_pixels: 4, zone_pixels: 900, area_m2: 400 },
        { threat: "water", zone: "inside", changed_pixels: 12, zone_pixels: 400, area_m2: 1200 },
      ]),
    );
    expect(strongest?.threat).toBe("water");
    expect(strongestSignal(scan([]))).toBeNull();
    expect(strongestSignal(null)).toBeNull();
  });

  it("writes areas in square metres or hectares", () => {
    expect(areaAr(1200)).toBe("١٬٢٠٠ م²");
    expect(areaAr(25_000)).toBe("٢٫٥ هكتار");
  });

  it("credits Copernicus for the year of the imagery", () => {
    expect(copernicusCredit(scan([]))).toContain("Copernicus Sentinel");
    expect(copernicusCredit(scan([]))).toContain("٢٠٢٦");
  });

  it("puts northern sites higher and eastern sites further right on the region map", () => {
    const sites = [site(24.73, 46.57), site(25.3, 45.6), site(24.2, 47.3)];
    const toPoint = project(sites);
    const [diriyah, north, east] = sites.map((s) => toPoint(s.location.lat, s.location.lon));
    expect(north[1]).toBeLessThan(diriyah[1]);
    expect(east[0]).toBeGreaterThan(diriyah[0]);
    for (const [x, y] of [diriyah, north, east]) {
      expect(x).toBeGreaterThanOrEqual(0);
      expect(x).toBeLessThanOrEqual(640);
      expect(y).toBeGreaterThanOrEqual(0);
      expect(y).toBeLessThanOrEqual(440);
    }
  });
});
