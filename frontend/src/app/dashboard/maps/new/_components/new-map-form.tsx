"use client";

import { useRouter } from "next/navigation";
import { type DragEvent, type FormEvent, useEffect, useState } from "react";
import { ApiError, type Site, request } from "@/lib/api";
import { createMap, type NewMapMeta } from "@/lib/maps";
import { useMe } from "@/lib/use-me";
import { AnalysisProgress } from "./analysis-progress";
import { CornerPicker, type Corners, DEFAULT_CORNERS, FULL_FRAME } from "./corner-picker";
import { Stepper } from "./stepper";

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
  const [dropping, setDropping] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (me) request<Site[]>("/sites").then(setSites);
  }, [me]);

  function choosePhoto(file: File | null) {
    if (photoUrl) URL.revokeObjectURL(photoUrl);
    setPhoto(file);
    setPhotoUrl(file ? URL.createObjectURL(file) : null);
    setCorners(DEFAULT_CORNERS);
    setError(null);
  }

  function onDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setDropping(false);
    const file = event.dataTransfer.files[0];
    if (file && ["image/jpeg", "image/png"].includes(file.type)) choosePhoto(file);
    else setError("أرسل صورة بصيغة JPEG أو PNG.");
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
      setError(e instanceof ApiError ? e.message : "تعذر إنشاء المخطط. تحقق من الاتصال وأعد المحاولة.");
      setPending(false);
    }
  }

  if (!me) return <p className="pt-6">…</p>;

  const step = pending ? 4 : photo ? 3 : wallChoice ? 2 : 1;

  return (
    <form onSubmit={submit} className="flex flex-col gap-6">
      <header className="flex flex-col gap-3">
        <h1 className="text-3xl font-bold leading-tight">ارسم مخطط جدار</h1>
        <Stepper current={step} steps={["اختر الجدار", "صوّر الجدار", "حدد الزوايا", "التحليل"]} />
      </header>

      <fieldset disabled={pending} className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
        <div className="flex flex-col gap-4">
          <label className="flex flex-col gap-1.5">
            <span className="font-bold">الجدار</span>
            <select
              required
              value={wallChoice}
              onChange={(e) => setWallChoice(e.target.value)}
              className="rounded-lg border border-clay/60 bg-white/80 p-2.5 text-base"
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
            <span className="text-sm text-mud">الواجهات المسجلة تعرف مقاسها؛ للجدار الآخر أدخل العرض والارتفاع.</span>
          </label>

          {wallChoice === OTHER_WALL && (
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="flex flex-col gap-1 sm:col-span-2">
                <span>اسم الجدار</span>
                <input name="wall_name" required maxLength={200} className="rounded-lg border border-clay/60 bg-white/80 p-2.5 text-base" />
              </label>
              <label className="flex flex-col gap-1">
                <span>العرض بالمتر</span>
                <input name="width_m" type="number" inputMode="decimal" step="0.1" min="0.5" max="500" required className="rounded-lg border border-clay/60 bg-white/80 p-2.5 text-base" />
              </label>
              <label className="flex flex-col gap-1">
                <span>الارتفاع بالمتر</span>
                <input name="height_m" type="number" inputMode="decimal" step="0.1" min="0.5" max="100" required className="rounded-lg border border-clay/60 bg-white/80 p-2.5 text-base" />
              </label>
            </div>
          )}

          <label
            onDragOver={(e) => {
              e.preventDefault();
              setDropping(true);
            }}
            onDragLeave={() => setDropping(false)}
            onDrop={onDrop}
            className={`flex cursor-pointer flex-col gap-1 rounded-xl border-2 border-dashed p-4 transition-colors ${
              dropping ? "border-sadu bg-sadu/5" : "border-clay/70 hover:border-mud"
            }`}
          >
            <span className="font-bold">{photo ? "غيّر الصورة" : "صوّر الجدار أو اسحب صورته هنا"}</span>
            <span className="text-sm text-mud">
              {photo ? photo.name : "قف أمام الجدار قدر الإمكان، في ضوء النهار، والجدار كاملًا في الإطار."}
            </span>
            <input
              type="file"
              accept="image/jpeg,image/png"
              capture="environment"
              required={!photo}
              className="sr-only"
              onChange={(e) => choosePhoto(e.target.files?.[0] ?? null)}
            />
          </label>

          {error && (
            <p role="alert" className="border-s-4 border-urgent bg-urgent/10 p-3 text-sm leading-relaxed">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={pending || !photo || !wallChoice}
            className="rounded-full bg-sadu px-8 py-3 text-lg font-bold text-sand transition-opacity disabled:opacity-40"
          >
            {pending ? "يحلّل أثر الجدار…" : "حلّل الجدار"}
          </button>
        </div>

        <div className="flex flex-col gap-2">
          {pending ? (
            <AnalysisProgress />
          ) : photoUrl ? (
            <>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm">اسحب النقاط الأربع إلى زوايا الجدار. تظهر عدسة مكبّرة أثناء السحب.</p>
                <div className="flex gap-2 text-sm">
                  <button type="button" onClick={() => setCorners(DEFAULT_CORNERS)} className="rounded-full border border-ink px-3 py-1">
                    أعد الزوايا
                  </button>
                  <button type="button" onClick={() => setCorners(FULL_FRAME)} className="rounded-full border border-ink px-3 py-1">
                    الصورة كاملة
                  </button>
                </div>
              </div>
              <CornerPicker imageUrl={photoUrl} corners={corners} onChange={setCorners} />
            </>
          ) : (
            <div className="flex aspect-[4/3] flex-col items-center justify-center gap-2 rounded-xl border border-clay/50 bg-white/40 p-6 text-center text-mud">
              <span className="text-lg font-bold text-ink">هنا تظهر صورة الجدار</span>
              <span className="max-w-xs text-sm leading-relaxed">بعد اختيار الصورة تحدد زواياه، فيعدّل أثر المنظور ويقسمه شبكة قبل التحليل.</span>
            </div>
          )}
        </div>
      </fieldset>
    </form>
  );
}
