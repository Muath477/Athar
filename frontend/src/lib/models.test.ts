import { describe, expect, it } from "vitest";
import { type DamageModel, metricLines, sortModels } from "@/lib/models";

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
