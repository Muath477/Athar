"use client";

import { type KeyboardEvent, useRef } from "react";

export type View = "place" | "model";

const VIEWS: { id: View; label: string }[] = [
  { id: "place", label: "المكان على الخريطة" },
  { id: "model", label: "نموذج الواجهات" },
];

type Props = { value: View; onChange: (view: View) => void };

export function ViewSwitch({ value, onChange }: Props) {
  const tabs = useRef<Record<View, HTMLButtonElement | null>>({ place: null, model: null });

  function moveFocus(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    event.preventDefault();
    const next = value === "place" ? "model" : "place";
    onChange(next);
    tabs.current[next]?.focus();
  }

  return (
    <div role="tablist" aria-label="طريقة العرض" onKeyDown={moveFocus} className="flex self-start rounded-sm border border-line p-0.5">
      {VIEWS.map((view) => {
        const selected = view.id === value;
        return (
          <button
            key={view.id}
            ref={(element) => {
              tabs.current[view.id] = element;
            }}
            id={`tab-${view.id}`}
            role="tab"
            aria-selected={selected}
            aria-controls={`view-${view.id}`}
            tabIndex={selected ? 0 : -1}
            onClick={() => onChange(view.id)}
            className={`min-h-11 cursor-pointer rounded-sm px-4 text-sm transition-colors duration-150 ${selected ? "bg-ink font-bold text-sand" : "text-ink hover:bg-accent"}`}
          >
            {view.label}
          </button>
        );
      })}
    </div>
  );
}
