"use client";

import { type KeyboardEvent, type PointerEvent, useRef, useState } from "react";

export type Corners = [number, number][];

const CORNER_NAMES = ["أعلى يسار الصورة", "أعلى يمين الصورة", "أسفل يمين الصورة", "أسفل يسار الصورة"];
const KEY_STEP = 0.01;

export const DEFAULT_CORNERS: Corners = [
  [0.08, 0.08],
  [0.92, 0.08],
  [0.92, 0.92],
  [0.08, 0.92],
];

export function CornerPicker({
  imageUrl,
  corners,
  onChange,
}: {
  imageUrl: string;
  corners: Corners;
  onChange: (corners: Corners) => void;
}) {
  const frame = useRef<HTMLDivElement>(null);
  const [dragging, setDragging] = useState<number | null>(null);

  function moveTo(index: number, x: number, y: number) {
    const next = corners.map((c) => [...c]) as Corners;
    next[index] = [clamp(x), clamp(y)];
    onChange(next);
  }

  function onPointerMove(event: PointerEvent<HTMLDivElement>) {
    if (dragging === null || !frame.current) return;
    const box = frame.current.getBoundingClientRect();
    moveTo(dragging, (event.clientX - box.left) / box.width, (event.clientY - box.top) / box.height);
  }

  function onKeyDown(index: number, event: KeyboardEvent<HTMLButtonElement>) {
    const [x, y] = corners[index];
    const moves: Record<string, [number, number]> = {
      ArrowLeft: [-KEY_STEP, 0],
      ArrowRight: [KEY_STEP, 0],
      ArrowUp: [0, -KEY_STEP],
      ArrowDown: [0, KEY_STEP],
    };
    const move = moves[event.key];
    if (!move) return;
    event.preventDefault();
    moveTo(index, x + move[0], y + move[1]);
  }

  const outline = corners.map(([x, y]) => `${x * 100},${y * 100}`).join(" ");

  return (
    <div
      ref={frame}
      dir="ltr"
      className="relative touch-none select-none overflow-hidden rounded-xl"
      onPointerMove={onPointerMove}
      onPointerUp={() => setDragging(null)}
      onPointerLeave={() => setDragging(null)}
    >
      <img src={imageUrl} alt="صورة الجدار" className="block w-full" draggable={false} />
      <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="pointer-events-none absolute inset-0 h-full w-full">
        <polygon points={outline} fill="rgba(143,31,26,0.15)" stroke="#8f1f1a" strokeWidth={0.6} />
      </svg>
      {corners.map(([x, y], index) => (
        <button
          key={CORNER_NAMES[index]}
          type="button"
          aria-label={`حرّك ${CORNER_NAMES[index]}`}
          onPointerDown={(event) => {
            event.currentTarget.setPointerCapture(event.pointerId);
            setDragging(index);
          }}
          onKeyDown={(event) => onKeyDown(index, event)}
          className="absolute flex h-8 w-8 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border-2 border-sand bg-sadu text-sm font-bold text-sand shadow"
          style={{ left: `${x * 100}%`, top: `${y * 100}%` }}
        >
          {index + 1}
        </button>
      ))}
    </div>
  );
}

function clamp(value: number): number {
  return Math.min(1, Math.max(0, Number(value.toFixed(4))));
}
