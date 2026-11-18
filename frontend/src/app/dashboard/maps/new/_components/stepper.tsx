export function Stepper({ steps, current }: { steps: string[]; current: number }) {
  return (
    <ol className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm" aria-label="خطوات رسم المخطط">
      {steps.map((label, index) => {
        const number = index + 1;
        const done = number < current;
        const active = number === current;
        return (
          <li key={label} aria-current={active ? "step" : undefined} className="flex items-center gap-2">
            <span
              className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold tabular-nums ${
                done ? "bg-ink text-sand" : active ? "bg-sadu text-sand" : "border border-clay text-mud"
              }`}
            >
              {done ? "✓" : number.toLocaleString("ar-SA")}
            </span>
            <span className={active ? "font-bold" : done ? "" : "text-mud"}>{label}</span>
            {number < steps.length && <span aria-hidden className="h-px w-6 bg-clay/60" />}
          </li>
        );
      })}
    </ol>
  );
}
