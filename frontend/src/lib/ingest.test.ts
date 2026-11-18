import { describe, expect, it } from "vitest";
import { batchSettled, checkPhotos, type IngestJob, MAX_BATCH_FILES, MAX_PHOTO_BYTES } from "./ingest";
import { mapSourceText } from "./labels";

function photo(name: string, type: string, size = 1024): File {
  const file = new File(["x"], name, { type });
  Object.defineProperty(file, "size", { value: size });
  return file;
}

function job(status: IngestJob["status"]): IngestJob {
  return { status } as IngestJob;
}

describe("checkPhotos", () => {
  it("accepts JPEG, PNG and HEIC even when the browser leaves the type empty", () => {
    const check = checkPhotos([photo("a.jpg", "image/jpeg"), photo("b.PNG", ""), photo("IMG_1.HEIC", "")], 0);
    expect(check.accepted.map((f) => f.name)).toEqual(["a.jpg", "b.PNG", "IMG_1.HEIC"]);
    expect(check.rejected).toEqual([]);
  });

  it("rejects other files and oversized photos with a reason", () => {
    const check = checkPhotos([photo("notes.pdf", "application/pdf"), photo("big.jpg", "image/jpeg", MAX_PHOTO_BYTES + 1)], 0);
    expect(check.accepted).toEqual([]);
    expect(check.rejected.map((r) => r.name)).toEqual(["notes.pdf", "big.jpg"]);
  });

  it("stops at the batch limit counting photos already chosen", () => {
    const check = checkPhotos([photo("1.jpg", "image/jpeg"), photo("2.jpg", "image/jpeg")], MAX_BATCH_FILES - 1);
    expect(check.accepted.map((f) => f.name)).toEqual(["1.jpg"]);
    expect(check.rejected.map((r) => r.name)).toEqual(["2.jpg"]);
  });
});

describe("batchSettled", () => {
  it("waits while any photo is queued or being analysed", () => {
    const base = { id: "b", total: 2, counts: {} };
    expect(batchSettled({ ...base, jobs: [job("done"), job("analysing")] })).toBe(false);
    expect(batchSettled({ ...base, jobs: [job("done"), job("needs_facade"), job("failed")] })).toBe(true);
  });
});

describe("mapSourceText", () => {
  it("names the camera that took the photo", () => {
    expect(mapSourceText("camera", "كاميرا البوابة")).toBe("كاميرا الموقع: كاميرا البوابة");
    expect(mapSourceText("upload", null)).toBe("رفع جماعي");
    expect(mapSourceText(null, null)).toBeNull();
  });
});
