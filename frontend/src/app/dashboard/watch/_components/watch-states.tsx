import { RetryAlert } from "@/app/_components/page-status";
import { Skeleton } from "@/components/ui/skeleton";
import { type Scan, imageryYear } from "@/lib/watch";

export function LoadError({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="mt-6">
      <RetryAlert message={message} onRetry={onRetry} />
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
        <Skeleton className="h-9 w-72 max-w-full animate-none" />
        <Skeleton className="h-4 w-full max-w-3xl animate-none" />
      </div>
      <div className="grid gap-6 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
        <Skeleton className="aspect-[16/11] max-lg:order-last animate-none" />
        <div className="flex flex-col gap-2">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-16 animate-none" />
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
        <Skeleton className="h-4 w-24 animate-none" />
        <Skeleton className="h-9 w-72 max-w-full animate-none" />
        <Skeleton className="h-4 w-full max-w-xl animate-none" />
      </div>
      <Skeleton className="h-11 w-40 animate-none" />
      <div className="grid gap-6 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]">
        <Skeleton className="aspect-square w-full max-w-xl animate-none" />
        <div className="flex flex-col gap-2">
          <Skeleton className="h-40 animate-none" />
        </div>
      </div>
    </div>
  );
}
