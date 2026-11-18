"use client";

import { useId, useState } from "react";
import type { WorkflowStep } from "@/lib/maps";

const CURRENT_BORDER: Record<WorkflowStep["state"], string> = {
  done: "border-ink/30",
  flagged: "border-moderate",
  waiting: "border-sadu",
  blocked: "border-urgent",
};

const STATE_AR: Record<WorkflowStep["state"], string> = {
  done: "تمّت",
  flagged: "تحتاج انتباه المختص",
  waiting: "بانتظار المختص",
  blocked: "متوقفة",
};

const STATE_TONE: Record<WorkflowStep["state"], string> = {
  done: "text-mud",
  flagged: "font-bold text-ink",
  waiting: "text-mud",
  blocked: "font-bold text-urgent",
};

const CRITERION_AR: Record<WorkflowStep["criterion"], string | null> = {
  none: null,
  privacy: "الخصوصية",
  accuracy: "دقة التحديد",
  reviewability: "سهولة المراجعة",
  map_clarity: "وضوح المخطط",
};

export function WorkflowSteps({ steps }: { steps: WorkflowStep[] }) {
  const [expanded, setExpanded] = useState(false);
  const listId = useId();
  const currentIndex = steps.findIndex((step) => step.state !== "done");
  const current = currentIndex === -1 ? null : steps[currentIndex];
  const done = currentIndex === -1 ? steps : steps.slice(0, currentIndex);
  const upcoming = currentIndex === -1 ? [] : steps.slice(currentIndex + 1);
  const collapsible = expanded ? "flex" : "hidden md:flex";

  return (
    <section aria-labelledby="workflow-title" className="flex flex-col gap-3 rounded-xl bg-white/60 p-3">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <h2 id="workflow-title" className="text-lg font-bold">
          خريطة الإجراءات
        </h2>
        <p className="text-sm text-mud">
          {current
            ? `الخطوة ${current.number.toLocaleString("ar-SA")} من ${steps.length.toLocaleString("ar-SA")}: ${current.title_ar}`
            : "اكتملت الخطوات كلها"}
        </p>
      </div>

      <ol id={listId} className="flex flex-wrap gap-2">
        {done.map((step) => (
          <li key={step.key} className={`${collapsible} md:w-auto`}>
            <details className="text-xs text-mud">
              <summary className="flex min-h-11 cursor-pointer list-none items-center gap-1.5 rounded-full bg-white/70 pe-3 ps-1.5">
                <StepNumber step={step} tone="bg-ink text-sand" />
                <span>{step.title_ar}</span>
              </summary>
              <div className="mt-1 flex max-w-xs flex-col gap-0.5 px-2 pb-1">
                <p className="text-sm text-ink">{step.output_ar}</p>
                <StepMeta step={step} />
              </div>
            </details>
          </li>
        ))}

        {current && (
          <li
            aria-current="step"
            className={`flex w-full flex-col gap-1 rounded-xl border-2 bg-white/80 p-3 ${CURRENT_BORDER[current.state]}`}
          >
            <div className="flex items-center gap-2">
              <StepNumber step={current} tone="bg-sadu text-sand" />
              <span className="font-bold">{current.title_ar}</span>
            </div>
            <p className="leading-relaxed">{current.output_ar}</p>
            <StepMeta step={current} />
          </li>
        )}

        {upcoming.map((step) => (
          <li key={step.key} className={`${collapsible} w-full`}>
            <details className="w-full text-sm">
              <summary className="flex min-h-11 cursor-pointer list-none flex-wrap items-center gap-x-2 gap-y-0.5">
                <StepNumber step={step} tone="border border-ink/30 text-ink" />
                <span>{step.title_ar}</span>
                <span className={`text-xs ${STATE_TONE[step.state]}`}>{STATE_AR[step.state]}</span>
              </summary>
              <div className="flex flex-col gap-0.5 pb-1 ps-8">
                <p>{step.output_ar}</p>
                <StepMeta step={step} />
              </div>
            </details>
          </li>
        ))}
      </ol>

      {steps.length > 1 && (
        <button
          type="button"
          aria-expanded={expanded}
          aria-controls={listId}
          onClick={() => setExpanded((open) => !open)}
          className="min-h-11 w-fit rounded-full border border-ink/30 px-4 text-sm hover:bg-ink hover:text-sand md:hidden"
        >
          {expanded ? "أخفِ بقية الخطوات" : "اعرض كل الخطوات"}
        </button>
      )}
    </section>
  );
}

function StepNumber({ step, tone }: { step: WorkflowStep; tone: string }) {
  return (
    <span aria-hidden="true" className={`grid size-6 shrink-0 place-items-center rounded-full text-xs font-bold ${tone}`}>
      {step.number.toLocaleString("ar-SA")}
    </span>
  );
}

function StepMeta({ step }: { step: WorkflowStep }) {
  const criterion = CRITERION_AR[step.criterion];
  return (
    <p className="text-xs text-mud">
      {step.actor === "specialist" ? "ينفذها المختص" : "ينفذها الوكيل"} ·{" "}
      <span className={STATE_TONE[step.state]}>{STATE_AR[step.state]}</span>
      {criterion && <> · المعيار: {criterion}</>}
    </p>
  );
}
