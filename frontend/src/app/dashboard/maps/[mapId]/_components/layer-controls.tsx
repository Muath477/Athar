"use client";

export type Layers = { opacity: number; grid: boolean; changes: boolean; hidden: string[] };

export function LayerControls({
  layers,
  onChange,
  hasChanges,
}: {
  layers: Layers;
  onChange: (layers: Layers) => void;
  hasChanges: boolean;
}) {
  return (
    <div className="no-print flex flex-wrap items-center gap-x-5 gap-y-2 text-sm">
      <label className="flex items-center gap-2">
        <span>شفافية الطبقة</span>
        <input
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={layers.opacity}
          onChange={(e) => onChange({ ...layers, opacity: Number(e.target.value) })}
          className="w-28 accent-sadu"
        />
      </label>
      <label className="flex items-center gap-1.5">
        <input type="checkbox" checked={layers.grid} onChange={(e) => onChange({ ...layers, grid: e.target.checked })} className="accent-sadu" />
        خطوط الشبكة
      </label>
      {hasChanges && (
        <label className="flex items-center gap-1.5">
          <input type="checkbox" checked={layers.changes} onChange={(e) => onChange({ ...layers, changes: e.target.checked })} className="accent-sadu" />
          ما تغيّر منذ آخر اعتماد
        </label>
      )}
    </div>
  );
}
