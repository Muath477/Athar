"use client";

import { useRouter } from "next/navigation";
import { type DragEvent, type FormEvent, useCallback, useEffect, useState } from "react";
import { PageSkeleton, RetryAlert } from "@/app/_components/page-status";
import { ApiError, type Site, request } from "@/lib/api";
import { createMap, type NewMapMeta } from "@/lib/maps";
import { useMeState } from "@/lib/use-me";
import { AnalysisProgress } from "./analysis-progress";
import { CornerPicker, type Corners, DEFAULT_CORNERS, FULL_FRAME } from "./corner-picker";
import { Stepper } from "./stepper";

const OTHER_WALL = "other";
const INPUT_CLASS = "min-h-11 rounded-lg border border-mud/60 bg-white px-3 text-base";
const SECONDARY_CLASS = "min-h-11 rounded-full border border-ink/30 px-4 hover:bg-ink hover:text-sand";

export function NewMapForm() {
  const { me, error: meError, retry: retryMe } = useMeState();
  const router = useRouter();
  const [sites, setSites] = useState<Site[]>([]);
  const [wallChoice, setWallChoice] = useState<string>("");
  const [photo, setPhoto] = useState<File | null>(null);
  const [photoUrl, setPhotoUrl] = useState<string | null>(null);
  const [corners, setCorners] = useState<Corners>(DEFAULT_CORNERS);
  const [pending, setPending] = useState(false);
  const [dropping, setDropping] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [photoError, setPhotoError] = useState<string | null>(null);
  const [sitesError, setSitesError] = useState<string | null>(null);

  const loadSites = useCallback(() => {
    request<Site[]>("/sites").then(setSites, (e) =>
      setSitesError(e instanceof ApiError ? e.message : "تعذر تحميل الجدران المسجلة."),
    );
  }, []);

  useEffect(() => {
    if (me) loadSites();
  }, [me, loadSites]);

  function choosePhoto(file: File | null) {
    if (photoUrl) URL.revokeObjectURL(photoUrl);
    setPhoto(file);
    setPhotoUrl(file ? URL.createObjectURL(file) : null);
    setCorners(DEFAULT_CORNERS);
    setError(null);
    setPhotoError(null);
  }

  function onDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setDropping(false);
    const file = event.dataTransfer.files[0];
    if (file && ["image/jpeg", "image/png"].includes(file.type)) choosePhoto(file);
    else setPhotoError("أرسل صورة بصيغة JPEG أو PNG.");
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

  if (meError) {
    return (
      <div className="pt-6">
        <RetryAlert message={meError} onRetry={retryMe} />
      </div>
    );
  }
  if (!me) return <FormSkeleton />;

  const step = pending ? 4 : photo ? 3 : wallChoice ? 2 : 1;
  const missing = !wallChoice && !photo
    ? "اختر الجدار وأرفق صورة أولًا."
    : !wallChoice
      ? "اختر الجدار أولًا."
      : !photo
        ? "أرفق صورة الجدار أولًا."
        : null;

  return (
    <form onSubmit={submit} className="flex flex-col gap-6">
      <header className="flex flex-col gap-3">
        <h1 className="text-3xl font-bold leading-snug">ارسم مخطط جدار</h1>
        <Stepper current={step} steps={["اختر الجدار", "صوّر الجدار", "حدد الزوايا", "التحليل"]} />
      </header>

      {sitesError && (
        <RetryAlert
          message={sitesError}
          onRetry={() => {
            setSitesError(null);
            loadSites();
          }}
        />
      )}

      <fieldset
        disabled={pending}
        className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,2fr)] lg:grid-rows-[auto_1fr]"
      >
        <div className="flex flex-col gap-4 lg:col-start-1 lg:row-start-1">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="wall-choice" className="font-bold">
              الجدار
            </label>
            <select
              id="wall-choice"
              required
              value={wallChoice}
              onChange={(e) => setWallChoice(e.target.value)}
              aria-describedby="wall-choice-hint"
              className="min-h-11 rounded-lg border border-mud/60 bg-white px-3 text-base"
            >
              <option value="" disabled>
                اختر الجدار
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
            <p id="wall-choice-hint" className="text-sm text-mud">
              الواجهات المسجلة تعرف مقاسها؛ للجدار غير المسجل أدخل العرض والارتفاع.
            </p>
          </div>

          {wallChoice === OTHER_WALL && (
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="flex flex-col gap-1 sm:col-span-2">
                <span>اسم الجدار</span>
                <input name="wall_name" required maxLength={200} className={INPUT_CLASS} />
              </label>
              <label className="flex flex-col gap-1">
                <span>العرض بالمتر</span>
                <input name="width_m" type="number" inputMode="decimal" step="0.1" min="0.5" max="500" required className={INPUT_CLASS} />
              </label>
              <label className="flex flex-col gap-1">
                <span>الارتفاع بالمتر</span>
                <input name="height_m" type="number" inputMode="decimal" step="0.1" min="0.5" max="100" required className={INPUT_CLASS} />
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
            className={`flex cursor-pointer flex-col gap-1 rounded-xl border-2 border-dashed p-4 transition-colors has-[:focus-visible]:outline has-[:focus-visible]:outline-[3px] has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-sadu ${
              dropping ? "border-sadu bg-white/60" : photoError ? "border-urgent" : "border-mud hover:bg-white/60"
            }`}
          >
            <span className="font-bold">{photo ? "غيّر الصورة" : "صوّر الجدار أو اسحب صورته هنا"}</span>
            <span className="text-sm text-mud">
              {photo ? <bdi>{photo.name}</bdi> : "قف أمام الجدار قدر الإمكان، في ضوء النهار، والجدار كاملًا في الإطار."}
            </span>
            <input
              type="file"
              accept="image/jpeg,image/png"
              capture="environment"
              required={!photo}
              aria-invalid={photoError ? true : undefined}
              aria-describedby={photoError ? "wall-photo-error" : undefined}
              className="sr-only"
              onChange={(e) => choosePhoto(e.target.files?.[0] ?? null)}
            />
          </label>
          {photoError && (
            <p id="wall-photo-error" role="alert" className="-mt-2 text-sm text-urgent">
              {photoError}
            </p>
          )}
        </div>

        <div className="flex flex-col gap-2 lg:col-start-2 lg:row-span-2 lg:row-start-1">
          {pending ? (
            <AnalysisProgress />
          ) : photoUrl ? (
            <>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm leading-relaxed">
                  اسحب النقاط الأربع إلى زوايا الجدار، أو اختر نقطة ثم انقر مكانها في الصورة. تظهر عدسة مكبّرة أثناء
                  السحب.
                </p>
                <div className="flex gap-2 text-sm">
                  <button type="button" onClick={() => setCorners(DEFAULT_CORNERS)} className={SECONDARY_CLASS}>
                    أعد الزوايا
                  </button>
                  <button type="button" onClick={() => setCorners(FULL_FRAME)} className={SECONDARY_CLASS}>
                    الصورة كاملة
                  </button>
                </div>
              </div>
              <CornerPicker imageUrl={photoUrl} corners={corners} onChange={setCorners} />
            </>
          ) : (
            <div className="flex aspect-[4/3] flex-col items-center justify-center gap-2 rounded-xl bg-white/60 p-6 text-center text-mud">
              <span className="text-lg font-bold text-ink">هنا تظهر صورة الجدار</span>
              <span className="max-w-xs text-sm leading-relaxed">بعد اختيار الصورة تحدد زواياه، فيعدّل أثر المنظور ويقسمه شبكة قبل التحليل.</span>
            </div>
          )}
        </div>

        <div className="flex flex-col gap-3 self-start lg:col-start-1 lg:row-start-2">
          {error && (
            <p role="alert" className="rounded-xl border border-urgent/40 bg-urgent/10 p-3 text-sm leading-relaxed">
              {error}
            </p>
          )}
          <button
            type="submit"
            disabled={pending || !photo || !wallChoice}
            aria-describedby={missing && !pending ? "submit-missing" : undefined}
            className="min-h-11 rounded-full bg-sadu px-6 text-lg font-bold text-sand hover:bg-ink disabled:opacity-50"
          >
            {pending ? "يحلّل أثر الجدار…" : "حلّل الجدار"}
          </button>
          {missing && !pending && (
            <p id="submit-missing" className="text-sm text-mud">
              {missing}
            </p>
          )}
        </div>
      </fieldset>
    </form>
  );
}

function FormSkeleton() {
  return (
    <PageSkeleton>
      <div className="flex flex-col gap-3">
        <div className="h-9 w-72 max-w-full rounded-xl bg-clay/25" />
        <div className="h-6 w-96 max-w-full rounded-xl bg-clay/20" />
      </div>
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
        <div className="flex flex-col gap-4">
          <div className="h-11 rounded-xl bg-clay/20" />
          <div className="h-24 rounded-xl bg-clay/20" />
        </div>
        <div className="aspect-[4/3] rounded-xl bg-clay/20" />
      </div>
    </PageSkeleton>
  );
}
