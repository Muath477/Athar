export type Forms = { zero?: string; one: string; two: string; few: string; many: string; hundred?: string };

export function countAr(count: number, forms: Forms): string {
  const n = Math.abs(count);
  const number = count.toLocaleString("ar-SA");
  if (n === 0 && forms.zero) return forms.zero;
  if (n === 1) return forms.one;
  if (n === 2) return forms.two;
  if (n % 100 >= 3 && n % 100 <= 10) return `${number} ${forms.few}`;
  if (n >= 100 && n % 100 <= 2) return `${number} ${forms.hundred ?? forms.many}`;
  return `${number} ${forms.many}`;
}

export const urgentCells: Forms = {
  one: "خلية عاجلة واحدة",
  two: "خليتان عاجلتان",
  few: "خلايا عاجلة",
  many: "خلية عاجلة",
};

export const corrections: Forms = { one: "تصحيحًا واحدًا", two: "تصحيحين", few: "تصحيحات", many: "تصحيحًا" };

export const maps: Forms = {
  zero: "لا مخططات بعد",
  one: "مخطط واحد",
  two: "مخططان",
  few: "مخططات",
  many: "مخططًا",
  hundred: "مخطط",
};

export const approvedMaps: Forms = {
  one: "مخطط معتمد واحد",
  two: "مخططين معتمدين",
  few: "مخططات معتمدة",
  many: "مخططًا معتمدًا",
  hundred: "مخطط معتمد",
};

export const scenes: Forms = { one: "صورة واحدة", two: "صورتين", few: "صور", many: "صورة" };

export const missions: Forms = { one: "مهمة تصوير واحدة", two: "مهمتا تصوير", few: "مهام تصوير", many: "مهمة تصوير" };

export const lowConfidenceElements: Forms = {
  one: "عنصرًا واحدًا بثقة منخفضة",
  two: "عنصرين بثقة منخفضة",
  few: "عناصر بثقة منخفضة",
  many: "عنصرًا بثقة منخفضة",
};

export const points: Forms = { one: "نقطة واحدة", two: "نقطتان", few: "نقاط", many: "نقطة" };

export const cells: Forms = { one: "خلية واحدة", two: "خليتان", few: "خلايا", many: "خلية", hundred: "خلية" };

export const elements: Forms = { zero: "لا عناصر", one: "عنصر واحد", two: "عنصران", few: "عناصر", many: "عنصرًا", hundred: "عنصر" };

export const urgentElements: Forms = {
  zero: "لا عناصر عاجلة",
  one: "عنصر عاجل واحد",
  two: "عنصران عاجلان",
  few: "عناصر عاجلة",
  many: "عنصرًا عاجلًا",
  hundred: "عنصر عاجل",
};

export const alerts: Forms = { one: "تنبيه واحد", two: "تنبيهان", few: "تنبيهات", many: "تنبيهًا", hundred: "تنبيه" };

export const hectares: Forms = { one: "هكتار واحد", two: "هكتاران", few: "هكتارات", many: "هكتارًا", hundred: "هكتار" };

export const days: Forms = { one: "يوم", two: "يومين", few: "أيام", many: "يومًا", hundred: "يوم" };

export const unsavedEdits: Forms = {
  one: "تعديل واحد غير محفوظ",
  two: "تعديلان غير محفوظين",
  few: "تعديلات غير محفوظة",
  many: "تعديلًا غير محفوظ",
  hundred: "تعديل غير محفوظ",
};

export const photos: Forms = {
  zero: "لا صور",
  one: "صورة واحدة",
  two: "صورتان",
  few: "صور",
  many: "صورة",
  hundred: "صورة",
};

export const devices: Forms = {
  zero: "لا أجهزة بعد",
  one: "جهاز واحد",
  two: "جهازان",
  few: "أجهزة",
  many: "جهازًا",
  hundred: "جهاز",
};

export const modelVersions: Forms = {
  zero: "لا إصدارات مسجلة بعد",
  one: "إصدار واحد",
  two: "إصداران",
  few: "إصدارات",
  many: "إصدارًا",
  hundred: "إصدار",
};
