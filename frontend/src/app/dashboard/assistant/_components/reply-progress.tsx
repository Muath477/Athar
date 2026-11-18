export type Step = { key: string; label: string; state: "running" | "done" | "failed" };

export type ReplyProgress = { skill: string | null; thinking: boolean; steps: Step[] };

const STATE_CLASS: Record<Step["state"], string> = {
  running: "bg-clay animate-pulse motion-reduce:animate-none",
  done: "bg-ink/60",
  failed: "bg-urgent",
};

const STATE_AR: Record<Step["state"], string> = { running: "جارٍ", done: "تم", failed: "تعذّر" };

export function ReplyTimeline({ progress }: { progress: ReplyProgress }) {
  return (
    <div aria-live="polite" aria-atomic="false" className="flex flex-col gap-2 rounded-xl border border-clay/40 bg-white/75 p-3">
      <p className="text-sm font-bold text-mud">المساعد يعمل{progress.skill ? <> · <bdi>{progress.skill}</bdi></> : null}</p>
      <ol aria-label="خطوات الرد" className="flex flex-col gap-1 text-sm">
        {progress.steps.map((step) => (
          <li key={step.key} className="flex items-center gap-2">
            <span aria-hidden="true" className={`inline-block size-2 shrink-0 rounded-full ${STATE_CLASS[step.state]}`} />
            <span className="sr-only">{STATE_AR[step.state]}: </span>
            <span className={step.state === "failed" ? "text-urgent" : undefined}>{step.label}</span>
          </li>
        ))}
        {progress.thinking && (
          <li className="flex items-center gap-2 text-mud">
            <span aria-hidden="true" className="inline-block size-2 shrink-0 animate-pulse rounded-full bg-clay motion-reduce:animate-none" />
            يخطط للخطوة التالية…
          </li>
        )}
      </ol>
    </div>
  );
}
