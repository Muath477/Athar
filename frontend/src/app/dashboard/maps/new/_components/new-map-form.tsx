"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useEffect, useState } from "react";
import { ApiError, type Site, request } from "@/lib/api";
import { createMap, type NewMapMeta } from "@/lib/maps";
import { useMe } from "@/lib/use-me";
import { CornerPicker, type Corners, DEFAULT_CORNERS } from "./corner-picker";

const OTHER_WALL = "other";

export function NewMapForm() {
  const me = useMe();
  const router = useRouter();
  const [sites, setSites] = useState<Site[]>([]);
  const [wallChoice, setWallChoice] = useState<string>("");
  const [photo, setPhoto] = useState<File | null>(null);
  const [photoUrl, setPhotoUrl] = useState<string | null>(null);
  const [corners, setCorners] = useState<Corners>(DEFAULT_CORNERS);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (me) request<Site[]>("/sites").then(setSites);
  }, [me]);

  function choosePhoto(file: File | null) {
    if (photoUrl) URL.revokeObjectURL(photoUrl);
    setPhoto(file);
    setPhotoUrl(file ? URL.createObjectURL(file) : null);
    setCorners(DEFAULT_CORNERS);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!photo) return;
    const form = new FormData(event.currentTarget);
    const meta: NewMapMeta = { corners };
    if (wallChoice === OTHER_WALL) {
      meta.wall_name = String(form.get("wall_name"));
      meta.width_m = Number(form.get("width_m"));
      meta.height_m = Number(form.get("height_m"));
    } else {
      meta.facade_id = wallChoice;
    }
    setPending(true);
    setError(null);
    try {
      const created = await createMap(photo, meta);
      router.push(`/dashboard/maps/${created.id}`);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "تعذر إنشاء المخطط.");
      setPending(false);
    }
  }

  if (!me) return <p className="pt-6">…</p>;

  return (
    <form onSubmit={submit} className="flex flex-col gap-4 pt-2">
      <h1 className="text-2xl font-bold">مخطط تلف جديد</h1>

      <label className="flex flex-col gap-1">
        <span className="font-bold">الجدار</span>
        <select
          required
          value={wallChoice}
          onChange={(e) => setWallChoice(e.target.value)}
          className="rounded-lg border bg-white/70 p-2"
        >
          <option value="" disabled>
            اختر واجهة مسجلة أو جدارًا آخر
          </option>
          {sites.map((site) => (
            <optgroup key={site.id} label={site.name_ar}>
              {site.facades.map((facade) => (
                <option key={facade.id} value={facade.id}>
                  {facade.name_ar}
                </option>
              ))}
            </optgroup>
          ))}
          <option value={OTHER_WALL}>جدار غير مسجل</option>
        </select>
      </label>

      {wallChoice === OTHER_WALL && (
        <fieldset className="grid gap-3 sm:grid-cols-3">
          <label className="flex flex-col gap-1">
            <span>اسم الجدار</span>
            <input name="wall_name" required maxLength={200} className="rounded-lg border bg-white/70 p-2" />
          </label>
          <label className="flex flex-col gap-1">
            <span>العرض (م)</span>
            <input name="width_m" type="number" step="0.1" min="0.5" max="500" required className="rounded-lg border bg-white/70 p-2" />
          </label>
          <label className="flex flex-col gap-1">
            <span>الارتفاع (م)</span>
            <input name="height_m" type="number" step="0.1" min="0.5" max="100" required className="rounded-lg border bg-white/70 p-2" />
          </label>
        </fieldset>
      )}

      <label className="flex flex-col gap-1">
        <span className="font-bold">صورة الجدار</span>
        <input
          type="file"
          accept="image/jpeg,image/png"
          capture="environment"
          required
          onChange={(e) => choosePhoto(e.target.files?.[0] ?? null)}
        />
      </label>

      {photoUrl && (
        <section className="flex flex-col gap-2">
          <p className="text-sm">اسحب النقاط الأربع إلى زوايا الجدار، ليُعدَّل منظوره قبل التحليل.</p>
          <CornerPicker imageUrl={photoUrl} corners={corners} onChange={setCorners} />
        </section>
      )}

      {error && (
        <p role="alert" className="rounded-lg bg-urgent/10 p-2 text-urgent">
          {error}
        </p>
      )}

      <button
        type="submit"
        disabled={pending || !photo}
        className="self-start rounded-full bg-sadu px-8 py-3 font-bold text-sand disabled:opacity-50"
      >
        {pending ? "نحلّل الجدار…" : "حلّل الجدار"}
      </button>
    </form>
  );
}
