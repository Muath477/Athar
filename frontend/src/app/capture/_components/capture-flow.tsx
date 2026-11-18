"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Camera } from "./camera";
import { ApiError, baselineUrl, ensurePassport, request } from "@/lib/api";
import { currentPosition, type Heading, watchHeading } from "@/lib/geo";

type Consent = { location: boolean; heading: boolean };

export function CaptureFlow() {
  const router = useRouter();
  const params = useSearchParams();
  const missionId = params.get("mission");
  const siteId = params.get("site");
  const facadeId = params.get("facade");

  const [consent, setConsent] = useState<Consent>({ location: !siteId, heading: false });
  const [heading, setHeading] = useState<Heading | null>(null);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!consent.heading) return;
    let stop: (() => void) | null = null;
    watchHeading(setHeading)
      .then((s) => (stop = s))
      .catch(() => setConsent((c) => ({ ...c, heading: false })));
    return () => stop?.();
  }, [consent.heading]);

  async function send(photo: Blob) {
    setSending(true);
    setError(null);
    try {
      const position = consent.location ? await currentPosition().catch(() => null) : null;
      if (!position && !siteId) {
        setError("نحتاج موقعك لنعرف المبنى، أو امسح رمز المبنى المعلّق عند مدخله.");
        return;
      }
      await ensurePassport();
      const meta = {
        captured_at: new Date().toISOString(),
        site_id: siteId,
        mission_id: missionId,
        lat: position?.lat,
        lon: position?.lon,
        gps_accuracy_m: position?.accuracy,
        heading_deg: heading?.degrees,
        heading_accuracy_deg: heading?.accuracy ?? undefined,
        consent,
      };
      const form = new FormData();
      form.append("photo", photo, "photo.jpg");
      form.append("meta", JSON.stringify(meta));
      const accepted = await request<{ observation_id: string }>("/observations", {
        method: "POST",
        body: form,
        headers: { "Idempotency-Key": crypto.randomUUID() },
      });
      router.push(`/observation?id=${accepted.observation_id}`);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "تعذر إرسال الصورة. حاول مرة أخرى.");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="flex flex-col gap-5 pt-4">
      <h1 className="text-3xl font-bold leading-snug">صوّر الواجهة من الأمام</h1>
      <p className="text-sm leading-relaxed">
        قف أمام الواجهة واجعلها تملأ الإطار.
        {facadeId && " طابق الصورة الباهتة فوق الكاميرا قدر الإمكان."}
      </p>

      <fieldset className="flex flex-col gap-2 rounded-xl bg-white/60 p-4 text-sm">
        <legend className="sr-only">الموافقات</legend>
        <label className="flex min-h-11 items-start gap-2">
          <input
            type="checkbox"
            checked={consent.location}
            onChange={(e) => setConsent({ ...consent, location: e.target.checked })}
            className="mt-0.5 size-5 shrink-0 accent-sadu"
          />
          <span>استخدم موقعي لتحديد المبنى. يُحذف الموقع بعد معرفة المبنى.</span>
        </label>
        <label className="flex min-h-11 items-start gap-2">
          <input
            type="checkbox"
            checked={consent.heading}
            onChange={(e) => setConsent({ ...consent, heading: e.target.checked })}
            className="mt-0.5 size-5 shrink-0 accent-sadu"
          />
          <span>استخدم اتجاه الجوال لمعرفة الواجهة.</span>
        </label>
      </fieldset>

      {sending ? (
        <p role="status" className="text-center text-lg">نرسل صورتك…</p>
      ) : (
        <Camera overlayUrl={facadeId ? baselineUrl(facadeId) : null} onPhoto={send} />
      )}
      {error && (
        <p role="alert" className="rounded-xl border border-urgent/40 bg-urgent/10 p-3">
          {error}
        </p>
      )}
    </div>
  );
}
