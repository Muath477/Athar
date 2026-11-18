export type ModelStatus = "candidate" | "active" | "retired";

export type DamageModel = {
  id: string;
  name: string;
  version: string;
  base_model: string;
  adapter_uri: string;
  metrics: Record<string, unknown>;
  status: ModelStatus;
  created_at: string;
  activated_at: string | null;
};

export const modelStatusAr: Record<ModelStatus, string> = {
  candidate: "مرشح للتفعيل",
  active: "مفعل في التحليل",
  retired: "خارج الخدمة",
};

const METRIC_LABELS: Record<string, string> = {
  json_valid_rate: "صحة صيغة الإجابة",
  macro_f1: "متوسط F1 للأنواع",
  micro_f1: "F1 الإجمالي",
  damaged_vs_sound_accuracy: "دقة التمييز بين السليم والمتضرر",
  test_maps: "مخططات الاختبار",
};

export const NOTEBOOK_URL =
  "https://colab.research.google.com/github/Muath477/Athar/blob/main/ml/notebooks/train_qwen35_damage.ipynb";
export const ML_DOCS_URL = "https://github.com/Muath477/Athar/blob/main/docs/ml/architecture.md";

export type MetricLine = { key: string; label: string; value: string };

export function metricLines(metrics: Record<string, unknown>): MetricLine[] {
  return Object.entries(metrics)
    .filter((entry): entry is [string, number] => typeof entry[1] === "number" && Number.isFinite(entry[1]))
    .map(([key, value]) => ({ key, label: METRIC_LABELS[key] ?? key, value: formatMetric(key, value) }));
}

export type MetricColumn = { key: string; label: string };

export function metricColumns(models: DamageModel[]): MetricColumn[] {
  const columns = new Map<string, string>();
  for (const model of models) {
    for (const line of metricLines(model.metrics)) {
      if (!columns.has(line.key)) columns.set(line.key, line.label);
    }
  }
  return Array.from(columns, ([key, label]) => ({ key, label }));
}

function formatMetric(key: string, value: number): string {
  if (Number.isInteger(value) && !key.endsWith("_rate")) return value.toLocaleString("ar-SA");
  if (value >= 0 && value <= 1) {
    return value.toLocaleString("ar-SA", { style: "percent", maximumFractionDigits: 1 });
  }
  return value.toLocaleString("ar-SA", { maximumFractionDigits: 3 });
}

export function sortModels(models: DamageModel[]): DamageModel[] {
  const order: Record<ModelStatus, number> = { active: 0, candidate: 1, retired: 2 };
  return [...models].sort(
    (a, b) => order[a.status] - order[b.status] || b.created_at.localeCompare(a.created_at),
  );
}
