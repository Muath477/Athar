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
    <div role="tablist" aria-label="طريقة العرض" onKeyDown={moveFocus} className="flex self-start rounded-full border border-mud p-1">
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
            className={`min-h-11 rounded-full px-4 text-sm transition-colors ${selected ? "bg-mud text-sand" : "text-ink"}`}
          >
            {view.label}
          </button>
        );
      })}
    </div>
  );
}
