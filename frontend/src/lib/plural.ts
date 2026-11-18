type Forms = { one: string; two: string; few: string; many: string };

export function countAr(count: number, forms: Forms): string {
  const n = Math.abs(count);
  const number = count.toLocaleString("ar-SA");
  if (n === 1) return forms.one;
  if (n === 2) return forms.two;
  if (n % 100 >= 3 && n % 100 <= 10) return `${number} ${forms.few}`;
  return `${number} ${forms.many}`;
}

export const urgentCells: Forms = {
  one: "خلية عاجلة واحدة",
  two: "خليتان عاجلتان",
  few: "خلايا عاجلة",
  many: "خلية عاجلة",
};

export const corrections: Forms = { one: "تصحيحًا واحدًا", two: "تصحيحين", few: "تصحيحات", many: "تصحيحًا" };

export const maps: Forms = { one: "مخطط واحد", two: "مخططان", few: "مخططات", many: "مخططًا" };

export const scenes: Forms = { one: "صورة واحدة", two: "صورتين", few: "صور", many: "صورة" };

export const missions: Forms = { one: "مهمة تصوير واحدة", two: "مهمتا تصوير", few: "مهام تصوير", many: "مهمة تصوير" };
