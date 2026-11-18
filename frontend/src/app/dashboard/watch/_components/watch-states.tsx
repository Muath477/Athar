import { type Scan, imageryYear } from "@/lib/watch";

export function LoadError({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div
      role="alert"
      className="mt-6 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-urgent/40 bg-urgent/10 p-3 text-sm"
    >
      <p>{message}</p>
      <button type="button" onClick={onRetry} className="min-h-11 rounded-full border border-ink/30 px-4">
        أعد المحاولة
      </button>
    </div>
  );
}

export function CopernicusCredit({ scan }: { scan: Scan | null }) {
  return (
    <p className="text-xs text-mud">
      يحتوي على بيانات <bdi dir="ltr">Copernicus Sentinel</bdi> معدّلة {imageryYear(scan)}
    </p>
  );
}

export function IndexSkeleton() {
  return (
    <div
      role="status"
      aria-label="جارٍ التحميل"
      className="flex animate-pulse flex-col gap-6 pt-6 motion-reduce:animate-none"
    >
      <div className="flex flex-col gap-2">
        <div className="h-9 w-72 max-w-full rounded-xl bg-clay/25" />
        <div className="h-4 w-full max-w-3xl rounded-xl bg-clay/20" />
      </div>
      <div className="grid gap-6 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
        <div className="aspect-[16/11] rounded-xl bg-clay/20 max-lg:order-last" />
        <div className="flex flex-col gap-2">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="h-16 rounded-xl bg-clay/20" />
          ))}
        </div>
      </div>
    </div>
  );
}

export function SiteWatchSkeleton() {
  return (
    <div
      role="status"
      aria-label="جارٍ التحميل"
      className="flex animate-pulse flex-col gap-6 pt-6 motion-reduce:animate-none"
    >
      <div className="flex flex-col gap-2">
        <div className="h-4 w-24 rounded-xl bg-clay/20" />
        <div className="h-9 w-72 max-w-full rounded-xl bg-clay/25" />
        <div className="h-4 w-full max-w-xl rounded-xl bg-clay/20" />
      </div>
      <div className="h-11 w-40 rounded-full bg-clay/20" />
      <div className="grid gap-6 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]">
        <div className="aspect-square w-full max-w-xl rounded-xl bg-clay/20" />
        <div className="flex flex-col gap-2">
          <div className="h-40 rounded-xl bg-clay/20" />
        </div>
      </div>
    </div>
  );
}
