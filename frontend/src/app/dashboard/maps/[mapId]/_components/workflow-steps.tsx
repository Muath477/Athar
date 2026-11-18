import type { WorkflowStep } from "@/lib/maps";

const STATE_STYLE: Record<WorkflowStep["state"], string> = {
  done: "border-ink/15 bg-white/80",
  flagged: "border-moderate bg-moderate/10",
  waiting: "border-dashed border-clay bg-sand",
  blocked: "border-urgent bg-urgent/10",
};

const STATE_AR: Record<WorkflowStep["state"], string> = {
  done: "تمّت",
  flagged: "تحتاج انتباه المختص",
  waiting: "بانتظار المختص",
  blocked: "متوقفة",
};

const CRITERION_AR: Record<WorkflowStep["criterion"], string | null> = {
  none: null,
  privacy: "الخصوصية",
  accuracy: "دقة التحديد",
  reviewability: "سهولة المراجعة",
  map_clarity: "وضوح الخريطة",
};

export function WorkflowSteps({ steps }: { steps: WorkflowStep[] }) {
  return (
    <section aria-labelledby="workflow-title" className="flex flex-col gap-2">
      <h2 id="workflow-title" className="text-lg font-bold">
        خريطة الإجراءات
      </h2>
      <ol className="grid gap-2 sm:grid-cols-2 xl:grid-cols-5">
        {steps.map((step) => (
          <li key={step.key} className={`flex flex-col gap-1 rounded-xl border p-2.5 text-sm ${STATE_STYLE[step.state]}`}>
            <div className="flex items-center gap-2">
              <span
                className={`grid size-6 shrink-0 place-items-center rounded-full text-xs font-bold ${
                  step.actor === "specialist" ? "bg-sadu text-sand" : "bg-ink text-sand"
                }`}
                aria-hidden="true"
              >
                {step.number.toLocaleString("ar-SA")}
              </span>
              <span className="font-bold">{step.title_ar}</span>
            </div>
            <p className="leading-snug">{step.output_ar}</p>
            <p className="text-xs text-mud">
              {step.actor === "specialist" ? "ينفذها المختص" : "ينفذها الوكيل"} · {STATE_AR[step.state]}
              {CRITERION_AR[step.criterion] && <> · المعيار: {CRITERION_AR[step.criterion]}</>}
            </p>
          </li>
        ))}
      </ol>
    </section>
  );
}
