"use client";

import Link from "next/link";
import { useState } from "react";
import { type Mission, request } from "@/lib/api";
import { currentPosition } from "@/lib/geo";

export function NearbyMissions() {
  const [missions, setMissions] = useState<Mission[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function look() {
    setLoading(true);
    setError(null);
    try {
      const position = await currentPosition();
      setMissions(await request<Mission[]>(`/missions/nearby?lat=${position.lat}&lon=${position.lon}`));
    } catch {
      setError("لم نتمكن من معرفة موقعك. يمكنك التصوير دون مهمة.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="flex flex-col gap-3 rounded-xl bg-white/75 p-4">
      <h2 className="text-xl font-bold">مهام قريبة منك</h2>
      <p className="text-sm">بعض الواجهات تحتاج صورة جديدة. صوّرها لتساعد في التأكد من حالتها.</p>
      {missions === null ? (
        <button
          type="button"
          onClick={look}
          disabled={loading}
          className="min-h-11 self-start rounded-full border border-ink/30 px-5 hover:bg-ink hover:text-sand disabled:opacity-50"
        >
          {loading ? "نبحث…" : "ابحث بموقعي الآن"}
        </button>
      ) : missions.length === 0 ? (
        <p>لا مهام قريبة منك الآن. يمكنك تصوير أي واجهة تراثية أمامك.</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {missions.map((m) => (
            <li key={m.id} className="flex items-center justify-between gap-3 rounded-xl bg-white/60 p-3">
              <span>{m.instruction_ar}</span>
              <Link
                href={`/capture?mission=${m.id}&site=${m.site_id}&facade=${m.facade_id}`}
                className="inline-flex min-h-11 shrink-0 items-center rounded-full bg-mud px-5 text-sand hover:bg-ink"
              >
                صوّر
              </Link>
            </li>
          ))}
        </ul>
      )}
      {error && <p role="alert" className="text-sm text-urgent">{error}</p>}
    </section>
  );
}
