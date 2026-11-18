export function PageSkeleton({ children }: { children?: React.ReactNode }) {
  return (
    <div
      role="status"
      aria-label="جارٍ التحميل"
      className="flex animate-pulse flex-col gap-6 pt-6 motion-reduce:animate-none"
    >
      {children ?? (
        <>
          <div className="h-9 w-72 max-w-full rounded-xl bg-clay/25" />
          <div className="h-40 rounded-xl bg-clay/20" />
        </>
      )}
    </div>
  );
}

export function RetryAlert({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div role="alert" className="flex flex-wrap items-center gap-3 rounded-xl border border-urgent/40 bg-urgent/10 p-3 text-sm">
      <span>{message}</span>
      <button
        type="button"
        onClick={onRetry}
        className="min-h-11 rounded-full border border-ink/30 px-4 hover:bg-ink hover:text-sand"
      >
        أعد المحاولة
      </button>
    </div>
  );
}
