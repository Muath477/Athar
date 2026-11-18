import { type LatLon, request } from "@/lib/api";

export type Threat = "water" | "vegetation_loss" | "construction" | "earthworks" | "sand";
export type Zone = "inside" | "ring";
export type RiskLevel = "unknown" | "stable" | "watch" | "moderate" | "urgent";
export type ScanStatus = "ok" | "insufficient_data" | "source_unavailable";

export type Signal = {
  threat: Threat;
  zone: Zone;
  changed_pixels: number;
  zone_pixels: number;
  area_m2: number;
};

export type Scan = {
  id: string;
  site_id: string;
  created_at: string;
  source: string;
  is_sample: boolean;
  status: ScanStatus;
  baseline_start: string;
  baseline_end: string;
  recent_start: string;
  recent_end: string;
  baseline_scenes: number;
  recent_scenes: number;
  valid_share: number;
  score: number;
  level: RiskLevel;
  signals: Signal[];
  before_url: string | null;
  after_url: string | null;
  change_url: string | null;
  acknowledged_at: string | null;
  ground_check_at: string | null;
  mission_ids: string[];
};

export type SiteRisk = {
  site_id: string;
  slug: string;
  name_ar: string;
  name_en: string;
  building_type: string;
  location: LatLon;
  facades: number;
  priority: number;
  scanning: boolean;
  latest: Scan | null;
  failed_attempt: Scan | null;
  trend: "new" | "rising" | "steady" | "falling" | null;
  confidence: "first_sighting" | "confirmed" | null;
  confirmed_threats: { threat: Threat; zone: Zone }[];
  alert: boolean;
};

export type WatchOverview = {
  source: string;
  is_sample: boolean;
  threat_colors: Record<Threat, string>;
  alerts_pending: number;
  sites: SiteRisk[];
};

export type GroundCheck = { scan: Scan; mission_ids: string[]; inspector_visit: boolean };

export function getOverview(): Promise<WatchOverview> {
  return request<WatchOverview>("/watch/sites");
}

export function listScans(siteId: string): Promise<Scan[]> {
  return request<Scan[]>(`/watch/sites/${siteId}/scans`);
}

const POLL_MS = 2000;
const POLL_LIMIT = 120;

export async function scanSite(siteId: string): Promise<void> {
  await request<{ site_id: string; queued: boolean }>(`/watch/sites/${siteId}/scans`, { method: "POST" });
  for (let attempt = 0; attempt < POLL_LIMIT; attempt++) {
    await new Promise((resolve) => setTimeout(resolve, POLL_MS));
    const overview = await getOverview();
    if (!overview.sites.find((s) => s.site_id === siteId)?.scanning) return;
  }
}

export function acknowledgeScan(scanId: string): Promise<Scan> {
  return request<Scan>(`/watch/scans/${scanId}/acknowledge`, { method: "POST" });
}

export function requestGroundCheck(scanId: string): Promise<GroundCheck> {
  return request<GroundCheck>(`/watch/scans/${scanId}/ground-check`, { method: "POST" });
}

export const threatAr: Record<Threat, string> = {
  water: "مياه راكدة",
  vegetation_loss: "إزالة نخيل أو غطاء نباتي",
  construction: "بناء أو سفلتة جديدة",
  earthworks: "حفر أو تغيّر في سطح الأرض",
  sand: "زحف رمال",
};

export const zoneAr: Record<Zone, string> = {
  inside: "داخل حدود الموقع",
  ring: "في محيط ١٥٠ م",
};

export const levelAr: Record<RiskLevel, string> = {
  unknown: "بلا حكم",
  stable: "مستقر",
  watch: "يُراقب",
  moderate: "متوسط",
  urgent: "عاجل",
};

export const statusAr: Record<ScanStatus, string> = {
  ok: "اكتمل الفحص",
  insufficient_data: "صور صافية غير كافية",
  source_unavailable: "تعذّر الوصول إلى صور الأقمار",
};

export const levelClass: Record<RiskLevel, string> = {
  unknown: "bg-clay/25 text-ink",
  stable: "bg-ink/10 text-ink",
  watch: "bg-watch text-ink",
  moderate: "bg-moderate text-ink",
  urgent: "bg-urgent text-white",
};

export const LEVEL_ORDER: RiskLevel[] = ["urgent", "moderate", "watch", "stable", "unknown"];

export function latestOk(scans: Scan[]): Scan | null {
  return scans.find((scan) => scan.status === "ok") ?? null;
}

export function strongestSignal(scan: Scan | null): Signal | null {
  if (!scan || scan.signals.length === 0) return null;
  return scan.signals.reduce((best, s) => (s.area_m2 > best.area_m2 ? s : best));
}

export function areaAr(m2: number): string {
  if (m2 >= 10_000) return `${(m2 / 10_000).toLocaleString("ar-SA", { maximumFractionDigits: 1 })} هكتار`;
  return `${Math.round(m2).toLocaleString("ar-SA")} م²`;
}

export function copernicusCredit(scan: Scan | null): string {
  const year = scan ? new Date(scan.recent_end).getFullYear() : new Date().getFullYear();
  return `يحتوي على بيانات Copernicus Sentinel معدّلة ${year.toLocaleString("ar-SA", { useGrouping: false })}`;
}

export const trendAr: Record<NonNullable<SiteRisk["trend"]>, string> = {
  new: "أول فحص",
  rising: "الخطر يتصاعد",
  steady: "مستقر منذ الفحص السابق",
  falling: "الخطر يتراجع",
};

export function warningAr(site: SiteRisk): string | null {
  if (!site.latest || site.latest.signals.length === 0) return null;
  if (site.confidence === "confirmed") return "تغيّر مؤكد في فحصين متتاليين";
  return "رصد أول، ينتظر التأكيد في الفحص القادم";
}
