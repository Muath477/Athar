"use client";

import { type KeyboardEvent, type PointerEvent, useRef, useState } from "react";
import { MIN_POINTS, cellLabelAt } from "@/lib/elements";
import type { DamageMap, Geometry, GlossaryEntry, MapElement } from "@/lib/maps";
import { countAr, points as pointForms } from "@/lib/plural";

export type Tool = "select" | Geometry;

type Props = {
  map: DamageMap;
  elements: MapElement[];
  glossary: Record<string, GlossaryEntry>;
  tool: Tool;
  draftKey: string;
  drawColor: string;
  selectedId: string | null;
  showGrid: boolean;
  onSelect: (id: string | null) => void;
  onDraw: (points: number[][]) => void;
};

const OPACITY = { watch: 0.3, moderate: 0.45, urgent: 0.6 } as const;
const ARROWS: Record<string, [number, number]> = {
  ArrowLeft: [-1, 0],
  ArrowRight: [1, 0],
  ArrowUp: [0, -1],
  ArrowDown: [0, 1],
};

export function ElementCanvas({
  map,
  elements,
  glossary,
  tool,
  draftKey,
  drawColor,
  selectedId,
  showGrid,
  onSelect,
  onDraw,
}: Props) {
  const svg = useRef<SVGSVGElement>(null);
  const [draft, setDraft] = useState<number[][]>([]);
  const [hover, setHover] = useState<number[] | null>(null);
  const [cursor, setCursor] = useState<number[] | null>(null);
  const [draftFor, setDraftFor] = useState(draftKey);
  if (draftFor !== draftKey) {
    setDraftFor(draftKey);
    setDraft([]);
    setHover(null);
    setCursor(null);
  }
  const drawing = tool !== "select";
  const aspect = map.rectified_height_px / map.rectified_width_px;

  function toWall(event: PointerEvent<SVGSVGElement>): number[] {
    const box = svg.current!.getBoundingClientRect();
    const x = Math.min(1, Math.max(0, (event.clientX - box.left) / box.width));
    const y = Math.min(1, Math.max(0, (event.clientY - box.top) / box.height));
    return [Math.round(x * 10000) / 10000, Math.round(y * 10000) / 10000];
  }

  function finish(points = draft) {
    const distinct = points.filter(
      (point, i) => i === 0 || Math.hypot(point[0] - points[i - 1][0], point[1] - points[i - 1][1]) > 0.004,
    );
    if (tool === "select" || distinct.length < MIN_POINTS[tool]) return;
    onDraw(distinct);
    setDraft([]);
  }

  function place(point: number[]) {
    if (tool === "point") {
      onDraw([point]);
      return;
    }
    setDraft((current) => [...current, point]);
  }

  function onPointerDown(event: PointerEvent<SVGSVGElement>) {
    if (drawing) place(toWall(event));
  }

  function onKeyDown(event: KeyboardEvent<SVGSVGElement>) {
    if (event.key === "Escape") {
      setDraft([]);
      setCursor(null);
      onSelect(null);
      return;
    }
    if (!drawing) return;
    const arrow = ARROWS[event.key];
    if (arrow) {
      event.preventDefault();
      const step = event.shiftKey ? 0.05 : 0.01;
      setCursor((current) => {
        const [x, y] = current ?? [0.5, 0.5];
        return [clampToWall(x + arrow[0] * step), clampToWall(y + arrow[1] * step)];
      });
      return;
    }
    if (event.key === " ") {
      event.preventDefault();
      place(cursor ?? [0.5, 0.5]);
      if (!cursor) setCursor([0.5, 0.5]);
      return;
    }
    if (event.key === "Enter") finish();
  }

  const guide = hover ?? cursor;
  const preview = guide && draft.length ? [...draft, guide] : draft;

  return (
    <div className="flex flex-col gap-2">
      <div className="relative overflow-hidden rounded-xl bg-mud/20" dir="ltr">
        <img src={map.rectified_url} alt={`صورة ${map.wall_name} بعد تصحيح المنظور`} className="block w-full" />
        <svg
          ref={svg}
          viewBox={`0 0 1000 ${1000 * aspect}`}
          className={`absolute inset-0 h-full w-full ${drawing ? "cursor-crosshair" : "cursor-default"}`}
          role="application"
          aria-label={
            drawing
              ? "لوحة الرسم: انقر لإضافة نقاط، أو حرّك المؤشر بالأسهم واضغط زر المسافة. انقر مرتين أو اضغط Enter للإنهاء، و Esc للإلغاء"
              : "مخطط عناصر التلف. لاختيار عنصر بلوحة المفاتيح استخدم جدول عناصر التلف أسفله."
          }
          tabIndex={0}
          onPointerDown={onPointerDown}
          onPointerMove={(event) => drawing && draft.length && setHover(toWall(event))}
          onPointerLeave={() => setHover(null)}
          onDoubleClick={() => finish()}
          onKeyDown={onKeyDown}
        >
          {showGrid && <GridLines rows={map.rows} cols={map.cols} aspect={aspect} />}
          {elements.map((element) => (
            <Shape
              key={element.id}
              element={element}
              color={glossary[element.damage_type]?.color ?? "#555"}
              aspect={aspect}
              selected={element.id === selectedId}
              interactive={!drawing}
              onSelect={() => onSelect(element.id)}
            />
          ))}
          {preview.length > 0 && (
            <polyline
              points={preview.map(([x, y]) => `${x * 1000},${y * 1000 * aspect}`).join(" ")}
              fill={tool === "area" ? drawColor : "none"}
              fillOpacity={0.25}
              stroke={drawColor}
              strokeWidth={3}
              strokeDasharray="6 4"
            />
          )}
          {drawing && cursor && (
            <g className="pointer-events-none" stroke={drawColor} strokeWidth={3}>
              <circle cx={cursor[0] * 1000} cy={cursor[1] * 1000 * aspect} r={14} fill="none" />
              <circle cx={cursor[0] * 1000} cy={cursor[1] * 1000 * aspect} r={3} fill={drawColor} />
            </g>
          )}
        </svg>
      </div>
      <p className="text-sm text-mud" aria-live="polite">
        {drawing && (
          <>
            {tool === "point" ? (
              "انقر على مكان كل فجوة أو جحر."
            ) : draft.length === 0 ? (
              `انقر لبدء ${tool === "area" ? "المضلع" : "الخط"}.`
            ) : (
              <>
                {countAr(draft.length, pointForms)}. انقر مرتين أو اضغط{" "}
                <kbd dir="ltr" className="rounded-sm border border-line bg-white px-1">
                  Enter
                </kbd>{" "}
                للإنهاء.
              </>
            )}
            {cursor && (
              <span className="ms-2">
                المؤشر عند الخلية <bdi>{cellLabelAt(cursor[0], cursor[1], map.rows, map.cols)}</bdi>.
              </span>
            )}
            {draft.length >= MIN_POINTS[tool] && tool !== "point" && (
              <button type="button" onClick={() => finish()} className="ms-3 min-h-11 font-bold text-sadu underline">
                أنهِ الرسم
              </button>
            )}
            {draft.length > 0 && (
              <button type="button" onClick={() => setDraft([])} className="ms-3 min-h-11 underline">
                ألغِ
              </button>
            )}
          </>
        )}
      </p>
    </div>
  );
}

function Shape({
  element,
  color,
  aspect,
  selected,
  interactive,
  onSelect,
}: {
  element: MapElement;
  color: string;
  aspect: number;
  selected: boolean;
  interactive: boolean;
  onSelect: () => void;
}) {
  const pts = element.points.map(([x, y]) => [x * 1000, y * 1000 * aspect]);
  const outline = color.toLowerCase() === "#f4f1ec" ? "#3c3c3c" : color;
  const common = {
    onPointerDown: interactive
      ? (event: PointerEvent<SVGElement>) => {
          event.stopPropagation();
          onSelect();
        }
      : undefined,
    className: interactive ? "cursor-pointer" : "pointer-events-none",
  };
  const halo = selected ? { stroke: "#ffffff", strokeWidth: 9 } : null;
  const [lx, ly] = pts[0];
  return (
    <g aria-label={element.id}>
      {element.geometry === "area" && (
        <>
          {halo && <polygon points={pts.map((p) => p.join(",")).join(" ")} fill="none" {...halo} />}
          <polygon
            {...common}
            points={pts.map((p) => p.join(",")).join(" ")}
            fill={color}
            fillOpacity={OPACITY[element.severity]}
            stroke={outline}
            strokeWidth={3}
            strokeDasharray={element.needs_review ? "8 5" : undefined}
          />
        </>
      )}
      {element.geometry === "line" && (
        <>
          {halo && <polyline points={pts.map((p) => p.join(",")).join(" ")} fill="none" {...halo} />}
          <polyline
            {...common}
            points={pts.map((p) => p.join(",")).join(" ")}
            fill="none"
            stroke={color}
            strokeWidth={6}
            strokeLinecap="round"
            strokeDasharray={element.needs_review ? "10 6" : undefined}
          />
        </>
      )}
      {element.geometry === "point" && (
        <circle {...common} cx={lx} cy={ly} r={selected ? 12 : 9} fill={color} stroke="#ffffff" strokeWidth={2} />
      )}
      <text x={lx + 10} y={ly - 10} className="pointer-events-none select-none" fontSize={22} fontWeight={700} fill="#ffffff" stroke="#000000" strokeWidth={4} paintOrder="stroke">
        {element.id}
      </text>
    </g>
  );
}

function clampToWall(value: number): number {
  return Math.min(1, Math.max(0, Math.round(value * 10000) / 10000));
}

function GridLines({ rows, cols, aspect }: { rows: number; cols: number; aspect: number }) {
  const height = 1000 * aspect;
  return (
    <g stroke="#ffffff" strokeOpacity={0.45} strokeWidth={1} className="pointer-events-none">
      {Array.from({ length: cols - 1 }, (_, i) => (
        <line key={`c${i}`} x1={((i + 1) * 1000) / cols} x2={((i + 1) * 1000) / cols} y1={0} y2={height} />
      ))}
      {Array.from({ length: rows - 1 }, (_, i) => (
        <line key={`r${i}`} x1={0} x2={1000} y1={((i + 1) * height) / rows} y2={((i + 1) * height) / rows} />
      ))}
    </g>
  );
}
