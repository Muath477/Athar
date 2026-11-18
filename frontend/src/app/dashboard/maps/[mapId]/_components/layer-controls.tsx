"use client";

import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";

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
      <label className="flex min-h-11 items-center gap-2">
        <span>شفافية الطبقة</span>
        <input
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={layers.opacity}
          onChange={(e) => onChange({ ...layers, opacity: Number(e.target.value) })}
          className="w-28 cursor-pointer accent-sadu"
        />
      </label>
      <div className="flex min-h-11 items-center gap-2">
        <Checkbox
          id="layer-grid"
          checked={layers.grid}
          onCheckedChange={(checked) => onChange({ ...layers, grid: checked === true })}
        />
        <Label htmlFor="layer-grid" className="text-ink">
          خطوط الشبكة
        </Label>
      </div>
      {hasChanges && (
        <div className="flex min-h-11 items-center gap-2">
          <Checkbox
            id="layer-changes"
            checked={layers.changes}
            onCheckedChange={(checked) => onChange({ ...layers, changes: checked === true })}
          />
          <Label htmlFor="layer-changes" className="text-ink">
            ما تغيّر منذ آخر اعتماد
          </Label>
        </div>
      )}
    </div>
  );
}
