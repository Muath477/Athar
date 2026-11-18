import { describe, expect, it } from "vitest";
import { type DamageModel, metricColumns, metricLines, sortModels } from "@/lib/models";

function model(id: string, status: DamageModel["status"], created_at: string): DamageModel {
  return {
    id,
    name: `athar-damage-${id}`,
    version: id,
    base_model: "unsloth/Qwen3.5-4B",
    adapter_uri: "hf://athar/lora",
    metrics: {},
    status,
    created_at,
    activated_at: null,
  };
}

describe("model registry helpers", () => {
  it("shows rates as Arabic percentages and counts as Arabic digits", () => {
    const lines = metricLines({ json_valid_rate: 0.975, test_maps: 12, macro_f1: 0.4123, note: "x" });
    expect(lines.map((line) => line.label)).toEqual(["صحة صيغة الإجابة", "مخططات الاختبار", "متوسط F1 للأنواع"]);
    expect(lines[0].value).toBe((0.975).toLocaleString("ar-SA", { style: "percent", maximumFractionDigits: 1 }));
    expect(lines[1].value).toBe("١٢");
  });

  it("builds one column per numeric metric across all versions, in first-seen order", () => {
    const first = { ...model("1", "active", "2026-11-01T00:00:00Z"), metrics: { macro_f1: 0.4, note: "x" } };
    const second = { ...model("2", "candidate", "2026-11-02T00:00:00Z"), metrics: { micro_f1: 0.5, macro_f1: 0.6 } };
    expect(metricColumns([first, second])).toEqual([
      { key: "macro_f1", label: "متوسط F1 للأنواع" },
      { key: "micro_f1", label: "F1 الإجمالي" },
    ]);
  });

  it("lists the active model first, then the newest candidates", () => {
    const sorted = sortModels([
      model("1", "retired", "2026-11-01T00:00:00Z"),
      model("2", "candidate", "2026-11-02T00:00:00Z"),
      model("3", "active", "2026-11-01T12:00:00Z"),
      model("4", "candidate", "2026-11-03T00:00:00Z"),
    ]);
    expect(sorted.map((m) => m.id)).toEqual(["3", "4", "2", "1"]);
  });
});
