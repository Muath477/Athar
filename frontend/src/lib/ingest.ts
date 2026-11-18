import { request } from "@/lib/api";

export type DeviceKind = "fixed_camera" | "drone" | "phone" | "upload";
export type JobStatus = "queued" | "analysing" | "needs_facade" | "done" | "failed";
export type MapSource = "inspector" | "camera" | "drone" | "upload";

export type Device = {
  id: string;
  kind: DeviceKind;
  name_ar: string;
  site_id: string | null;
  facade_id: string | null;
  snapshot_url: string | null;
  rtsp_url: string | null;
  username: string | null;
  secret_env: string | null;
  secret_configured: boolean;
  interval_h: number | null;
  active: boolean;
  last_capture_at: string | null;
  last_status: "ok" | "failed" | null;
  last_error_ar: string | null;
  thumbnail_url: string | null;
  created_at: string;
};

export type DeviceInput = {
  kind: DeviceKind;
  name_ar: string;
  site_id: string | null;
  facade_id: string | null;
  snapshot_url: string | null;
  rtsp_url: string | null;
  username: string | null;
  secret_env: string | null;
  interval_h: number | null;
  active: boolean;
};

export type IngestJob = {
  id: string;
  batch_id: string | null;
  device_id: string | null;
  source: MapSource;
  source_label: string | null;
  file_name: string;
  status: JobStatus;
  attempts: number;
  error_ar: string | null;
  can_retry: boolean;
  photo_url: string | null;
  site_id: string | null;
  facade_id: string | null;
  map_id: string | null;
  lat: number | null;
  lon: number | null;
  taken_at: string | null;
  facade_match: "chosen" | "device" | "gps" | null;
  created_at: string;
  updated_at: string;
  finished_at: string | null;
};

export type UploadBatch = {
  id: string;
  total: number;
  counts: Partial<Record<JobStatus, number>>;
  jobs: IngestJob[];
};

export type UploadPlacement = { site_id?: string; facade_id?: string; device_id?: string };

export type PhotoCheck = { accepted: File[]; rejected: { name: string; reason: string }[] };

export const MAX_BATCH_FILES = 30;
export const MAX_PHOTO_BYTES = 8 * 1024 * 1024;
export const PHOTO_ACCEPT = "image/jpeg,image/png,image/heic,image/heif,.heic,.heif";

const PHOTO_NAME = /\.(jpe?g|png|heic|heif)$/i;
const PHOTO_TYPES = new Set(["image/jpeg", "image/png", "image/heic", "image/heif"]);
const SETTLED: ReadonlySet<JobStatus> = new Set(["done", "failed", "needs_facade"]);

export function isSettled(status: JobStatus): boolean {
  return SETTLED.has(status);
}

export function batchSettled(batch: UploadBatch): boolean {
  return batch.jobs.every((job) => isSettled(job.status));
}

export function checkPhotos(files: File[], alreadyChosen: number): PhotoCheck {
  const check: PhotoCheck = { accepted: [], rejected: [] };
  for (const file of files) {
    if (!PHOTO_TYPES.has(file.type) && !PHOTO_NAME.test(file.name)) {
      check.rejected.push({ name: file.name, reason: "ليست صورة JPEG أو PNG أو HEIC." });
    } else if (file.size > MAX_PHOTO_BYTES) {
      check.rejected.push({ name: file.name, reason: "أكبر من ٨ ميغابايت." });
    } else if (alreadyChosen + check.accepted.length >= MAX_BATCH_FILES) {
      check.rejected.push({ name: file.name, reason: "تجاوزت ٣٠ صورة في الدفعة." });
    } else {
      check.accepted.push(file);
    }
  }
  return check;
}

export function listDevices(): Promise<Device[]> {
  return request<Device[]>("/ingest/devices");
}

export function createDevice(input: DeviceInput): Promise<Device> {
  return request<Device>("/ingest/devices", { method: "POST", body: JSON.stringify(input) });
}

export function updateDevice(deviceId: string, input: DeviceInput): Promise<Device> {
  return request<Device>(`/ingest/devices/${deviceId}`, { method: "POST", body: JSON.stringify(input) });
}

export function deleteDevice(deviceId: string): Promise<void> {
  return request<void>(`/ingest/devices/${deviceId}`, { method: "DELETE" });
}

export function captureNow(deviceId: string): Promise<IngestJob> {
  return request<IngestJob>(`/ingest/devices/${deviceId}/capture`, { method: "POST" });
}

export function deviceHistory(deviceId: string): Promise<IngestJob[]> {
  return request<IngestJob[]>(`/ingest/jobs?device_id=${encodeURIComponent(deviceId)}&limit=20`);
}

export function uploadPhotos(files: File[], placement: UploadPlacement): Promise<UploadBatch> {
  const body = new FormData();
  for (const file of files) body.append("files", file);
  for (const [field, value] of Object.entries(placement)) if (value) body.append(field, value);
  return request<UploadBatch>("/ingest/uploads", { method: "POST", body });
}

export function getBatch(batchId: string): Promise<UploadBatch> {
  return request<UploadBatch>(`/ingest/batches/${batchId}`);
}

export function retryJob(jobId: string): Promise<IngestJob> {
  return request<IngestJob>(`/ingest/jobs/${jobId}/retry`, { method: "POST" });
}

export function assignFacade(jobId: string, facadeId: string): Promise<IngestJob> {
  return request<IngestJob>(`/ingest/jobs/${jobId}/facade`, {
    method: "POST",
    body: JSON.stringify({ facade_id: facadeId }),
  });
}
