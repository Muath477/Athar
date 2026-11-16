
const BASE = "/api/v1";
const PASSPORT_KEY = "sadu.passport";
const CSRF_KEY = "sadu.csrf";

export type Facade = {
  id: string;
  code: string;
  name_ar: string;
  name_en: string;
  outward_azimuth_deg: number;
  corners: number[][];
  default_camera: { position?: number[]; target?: number[] };
};

export type Site = {
  id: string;
  slug: string;
  name_ar: string;
  name_en: string;
  building_type: string;
  model_url: string | null;
  facades: Facade[];
};

export type ObservationStatus = "received" | "processing" | "needs_input" | "needs_retake" | "done" | "failed";

export type FindingSummary = { id: string; damage_type: string; severity: string; label: string; status: string };

export type ObservationDetail = {
  stage?: string;
  question_id?: string;
  options?: { facade_id: string; name_ar: string; name_en: string }[];
  site_found?: boolean;
  site_id?: string;
  facade_id?: string | null;
  story_id?: string | null;
  retake_reason?: string | null;
  findings?: FindingSummary[];
  passport_stamped?: boolean;
  error?: string;
};

export type ObservationState = { status: ObservationStatus; detail: ObservationDetail };

export type Claim = {
  claim_id: string;
  text: string;
  label: "confirmed" | "oral_account" | "interpretation" | "unknown";
  source: { title: string; url: string | null; narrator_name: string | null } | null;
};

export type Story = {
  story_id: string | null;
  site_id: string;
  facade_id: string | null;
  claims: Claim[];
  message: string | null;
  audio_url: string | null;
};

export type Finding = {
  id: string;
  facade_id: string;
  damage_type: string;
  severity: "watch" | "moderate" | "urgent";
  label: "confirmed" | "likely" | "unknown";
  status: string;
  confirmations: number;
  region_uv: number[];
  pin_xyz: number[];
  cause: string | null;
  cause_label: string;
  rationale_ar: string;
  created_at: string;
  evidence: { baseline_url: string | null; photo_url: string | null; diff_url: string | null } | null;
};

export type Mission = {
  id: string;
  site_id: string;
  facade_id: string;
  reason: string;
  instruction_ar: string;
  baseline_url: string;
  expires_at: string;
};

export type Coverage = {
  facade_id: string;
  code: string;
  name_ar: string;
  days_since_last_photo: number | null;
  open_mission_id: string | null;
};

export type Me = { id: string; email: string; role: "inspector" | "expert" | "admin"; csrf_token: string | null };

export type Passport = {
  passport_id: string;
  created_at: string;
  stamps: { site_id: string; site_name_ar: string; site_name_en: string; stamped_at: string }[];
};

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
  ) {
    super(message);
  }
}

export function passportToken(): string | null {
  return readStorage(PASSPORT_KEY);
}

export async function ensurePassport(): Promise<string> {
  const existing = passportToken();
  if (existing) return existing;
  const created = await request<{ token: string }>("/passports", { method: "POST" });
  writeStorage(PASSPORT_KEY, created.token);
  return created.token;
}

export function forgetPassportLocally(): void {
  removeStorage(PASSPORT_KEY);
}

export function rememberCsrf(token: string | null): void {
  if (token) writeStorage(CSRF_KEY, token);
  else removeStorage(CSRF_KEY);
}

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const passport = passportToken();
  if (passport) headers.set("X-Passport-Token", passport);
  const csrf = readStorage(CSRF_KEY);
  if (csrf && init.method && init.method !== "GET") headers.set("X-CSRF-Token", csrf);
  if (init.body && typeof init.body === "string") headers.set("Content-Type", "application/json");
  headers.set("Accept-Language", "ar");

  const response = await fetch(`${BASE}${path}`, { ...init, headers, credentials: "same-origin" });
  if (!response.ok) {
    const problem = await response.json().catch(() => ({}));
    throw new ApiError(response.status, problem.code ?? "http_error", problem.detail ?? response.statusText);
  }
  return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
}

export function eventsUrl(observationId: string): string {
  return `${BASE}/observations/${observationId}/events`;
}

export function baselineUrl(facadeId: string): string {
  return `${BASE}/facades/${facadeId}/baseline`;
}

function readStorage(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function writeStorage(key: string, value: string): void {
  try {
    window.localStorage.setItem(key, value);
  } catch {
  }
}

function removeStorage(key: string): void {
  try {
    window.localStorage.removeItem(key);
  } catch {
  }
}
