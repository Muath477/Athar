"use client";

import Link from "next/link";
import { useState } from "react";
import { Button, buttonVariants } from "@/components/ui/button";
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
    <section className="flex flex-col gap-3 rounded-sm border border-line bg-white p-4">
      <h2 className="text-xl font-bold">مهام قريبة منك</h2>
      <p className="text-sm">بعض الواجهات تحتاج صورة جديدة. صوّرها لتساعد في التأكد من حالتها.</p>
      {missions === null ? (
        <Button type="button" variant="outline" onClick={look} disabled={loading} className="self-start">
          {loading ? "نبحث…" : "ابحث بموقعي الآن"}
        </Button>
      ) : missions.length === 0 ? (
        <p>لا مهام قريبة منك الآن. يمكنك تصوير أي واجهة تراثية أمامك.</p>
      ) : (
        <ul className="flex flex-col divide-y divide-line border-t border-line">
          {missions.map((m) => (
            <li key={m.id} className="flex items-center justify-between gap-3 py-2">
              <span>{m.instruction_ar}</span>
              <Link
                href={`/capture?mission=${m.id}&site=${m.site_id}&facade=${m.facade_id}`}
                className={buttonVariants({ variant: "outline", size: "sm" })}
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
