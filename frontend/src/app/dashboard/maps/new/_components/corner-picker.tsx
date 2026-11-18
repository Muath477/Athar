"use client";

import { type KeyboardEvent, type MouseEvent, type PointerEvent, useRef, useState } from "react";

export type Corners = [number, number][];

const CORNER_NAMES = ["أعلى يسار الجدار", "أعلى يمين الجدار", "أسفل يمين الجدار", "أسفل يسار الجدار"];
const KEY_STEP = 0.005;
const LOUPE_SIZE = 128;
const LOUPE_ZOOM = 3;

export const DEFAULT_CORNERS: Corners = [
  [0.08, 0.08],
  [0.92, 0.08],
  [0.92, 0.92],
  [0.08, 0.92],
];

export const FULL_FRAME: Corners = [
  [0, 0],
  [1, 0],
  [1, 1],
  [0, 1],
];

type Frame = { width: number; height: number };

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
  const [size, setSize] = useState<Frame | null>(null);
  const [selected, setSelected] = useState(0);
  const [announcement, setAnnouncement] = useState("");

  function moveTo(index: number, x: number, y: number) {
    const next = corners.map((c) => [...c]) as Corners;
    next[index] = [clamp(x), clamp(y)];
    onChange(next);
    return next[index];
  }

  function announce(index: number, [x, y]: [number, number]) {
    setAnnouncement(
      `الزاوية ${(index + 1).toLocaleString("ar-SA")}: ${percent(x)} أفقيًا، ${percent(y)} رأسيًا`,
    );
  }

  function onFrameClick(event: MouseEvent<HTMLDivElement>) {
    if (!frame.current || (event.target as Element).closest("button")) return;
    const box = frame.current.getBoundingClientRect();
    const point = moveTo(selected, (event.clientX - box.left) / box.width, (event.clientY - box.top) / box.height);
    announce(selected, point);
  }

  function onPointerMove(event: PointerEvent<HTMLDivElement>) {
    if (dragging === null || !frame.current) return;
    const box = frame.current.getBoundingClientRect();
    setSize({ width: box.width, height: box.height });
    moveTo(dragging, (event.clientX - box.left) / box.width, (event.clientY - box.top) / box.height);
  }

  function onKeyDown(index: number, event: KeyboardEvent<HTMLButtonElement>) {
    const [x, y] = corners[index];
    const step = event.shiftKey ? KEY_STEP * 5 : KEY_STEP;
    const moves: Record<string, [number, number]> = {
      ArrowLeft: [-step, 0],
      ArrowRight: [step, 0],
      ArrowUp: [0, -step],
      ArrowDown: [0, step],
    };
    const move = moves[event.key];
    if (!move) return;
    event.preventDefault();
    announce(index, moveTo(index, x + move[0], y + move[1]));
  }

  const outline = corners.map(([x, y]) => `${x * 100},${y * 100}`).join(" ");
  const active = dragging !== null ? corners[dragging] : null;

  return (
    <div className="flex flex-col gap-2">
      <div
        ref={frame}
        dir="ltr"
        className="relative cursor-crosshair touch-none select-none overflow-hidden rounded-xl bg-ink"
        onPointerMove={onPointerMove}
        onPointerUp={() => setDragging(null)}
        onPointerCancel={() => setDragging(null)}
        onClick={onFrameClick}
      >
        <img src={imageUrl} alt="صورة الجدار قبل تعديل المنظور" className="block w-full" draggable={false} />
        <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="pointer-events-none absolute inset-0 h-full w-full">
          <defs>
            <mask id="wall-outline">
              <rect width="100" height="100" fill="white" />
              <polygon points={outline} fill="black" />
            </mask>
          </defs>
          <rect width="100" height="100" fill="var(--color-ink)" fillOpacity={0.45} mask="url(#wall-outline)" />
          <polygon points={outline} fill="none" stroke="var(--color-sand)" strokeWidth={0.5} vectorEffect="non-scaling-stroke" />
        </svg>
        {corners.map(([x, y], index) => (
          <button
            key={CORNER_NAMES[index]}
            type="button"
            aria-label={`حرّك زاوية ${CORNER_NAMES[index]} بالأسهم`}
            aria-pressed={selected === index}
            onFocus={() => setSelected(index)}
            onPointerDown={(event) => {
              setSelected(index);
              event.currentTarget.setPointerCapture(event.pointerId);
              const box = frame.current?.getBoundingClientRect();
              if (box) setSize({ width: box.width, height: box.height });
              setDragging(index);
            }}
            onKeyDown={(event) => onKeyDown(index, event)}
            className={`absolute flex h-11 w-11 -translate-x-1/2 -translate-y-1/2 cursor-grab items-center justify-center rounded-full border-2 border-sand text-sm font-bold text-sand shadow transition-transform focus-visible:outline-sand active:cursor-grabbing motion-reduce:transition-none ${
              dragging === index ? "scale-75 bg-ink" : "bg-sadu"
            } ${selected === index ? "ring-2 ring-sand ring-offset-2 ring-offset-ink" : ""}`}
            style={{ left: `${x * 100}%`, top: `${y * 100}%` }}
          >
            {(index + 1).toLocaleString("ar-SA")}
          </button>
        ))}
        {active && size && <Loupe imageUrl={imageUrl} point={active} frame={size} />}
      </div>
      <p aria-live="polite" className="min-h-5 text-sm text-mud">
        {announcement}
      </p>
    </div>
  );
}

function Loupe({ imageUrl, point, frame }: { imageUrl: string; point: [number, number]; frame: Frame }) {
  const [x, y] = point;
  const above = y > 0.3;
  const left = Math.min(Math.max(x * frame.width - LOUPE_SIZE / 2, 4), frame.width - LOUPE_SIZE - 4);
  const top = above ? y * frame.height - LOUPE_SIZE - 28 : y * frame.height + 28;
  return (
    <div
      aria-hidden
      className="pointer-events-none absolute overflow-hidden rounded-full border-4 border-sand shadow-lg"
      style={{
        left,
        top,
        width: LOUPE_SIZE,
        height: LOUPE_SIZE,
        backgroundImage: `url(${imageUrl})`,
        backgroundSize: `${frame.width * LOUPE_ZOOM}px ${frame.height * LOUPE_ZOOM}px`,
        backgroundPosition: `${LOUPE_SIZE / 2 - x * frame.width * LOUPE_ZOOM}px ${LOUPE_SIZE / 2 - y * frame.height * LOUPE_ZOOM}px`,
      }}
    >
      <span className="absolute left-1/2 top-0 h-full w-px -translate-x-1/2 bg-sadu" />
      <span className="absolute left-0 top-1/2 h-px w-full -translate-y-1/2 bg-sadu" />
    </div>
  );
}

function percent(value: number): string {
  return `${Math.round(value * 100).toLocaleString("ar-SA")}٪`;
}

function clamp(value: number): number {
  return Math.min(1, Math.max(0, Number(value.toFixed(4))));
}
