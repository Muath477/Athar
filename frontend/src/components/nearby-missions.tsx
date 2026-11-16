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
      // The position is sent for this answer only; the server does not store it.
      setMissions(await request<Mission[]>(`/missions/nearby?lat=${position.lat}&lon=${position.lon}`));
    } catch {
      setError("لم نتمكن من معرفة موقعك. يمكنك التصوير دون مهمة.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="flex flex-col gap-3 rounded-xl border border-clay/40 p-4">
      <h2 className="text-xl font-bold">مهام قريبة منك</h2>
      <p className="text-sm">بعض الواجهات تحتاج صورة جديدة. صوّرها لتساعد في التأكد من حالتها.</p>
      {missions === null ? (
        <button onClick={look} disabled={loading} className="self-start rounded-full border border-ink px-5 py-2">
          {loading ? "نبحث…" : "ابحث بموقعي الآن"}
        </button>
      ) : missions.length === 0 ? (
        <p>لا توجد مهام قريبة الآن.</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {missions.map((m) => (
            <li key={m.id} className="flex items-center justify-between gap-3 rounded-lg bg-white/70 p-3">
              <span>{m.instruction_ar}</span>
              <Link
                href={`/capture?mission=${m.id}&site=${m.site_id}&facade=${m.facade_id}`}
                className="shrink-0 rounded-full bg-mud px-4 py-1 text-sand"
              >
                صوّر
              </Link>
            </li>
          ))}
        </ul>
      )}
      {error && <p className="text-sm text-urgent">{error}</p>}
    </section>
  );
}
