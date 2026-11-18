import { TriangleAlertIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

export function PageSkeleton({ children }: { children?: React.ReactNode }) {
  return (
    <div
      role="status"
      aria-label="جارٍ التحميل"
      className="flex animate-pulse flex-col gap-6 pt-6 motion-reduce:animate-none"
    >
      {children ?? (
        <>
          <Skeleton className="h-9 w-72 max-w-full animate-none" />
          <Skeleton className="h-40 animate-none" />
        </>
      )}
    </div>
  );
}

export function RetryAlert({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div
      role="alert"
      className="flex flex-wrap items-center gap-3 rounded-sm border border-urgent/40 bg-urgent/5 p-3 text-sm"
    >
      <TriangleAlertIcon className="size-5 shrink-0 text-urgent" aria-hidden="true" />
      <span className="min-w-0 flex-1">{message}</span>
      <Button type="button" variant="outline" size="sm" onClick={onRetry}>
        أعد المحاولة
      </Button>
    </div>
  );
}
