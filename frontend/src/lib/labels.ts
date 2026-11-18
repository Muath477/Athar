
export const damageTypeAr: Record<string, string> = {
  crack: "التشققات",
  plaster_loss: "فقدان اللياسة",
  basal_erosion: "تآكل القاعدة",
  rain_gully: "أخاديد الأمطار",
  salt_efflorescence: "تزهّر الأملاح",
  cavity: "الفجوات والجحور",
  wall_head: "تلف رؤوس الجدران والشرفات",
  cement_repair: "ترميمات إسمنتية سابقة",
  surface_erosion: "تآكل السطح",
  moisture: "رطوبة",
  missing_element: "عنصر مفقود",
  partial_collapse: "انهيار جزئي",
  graffiti: "كتابة على الجدار",
  new_construction: "بناء مستحدث",
  other: "تغير غير مصنف",
  none: "لا تغير",
};

export const severityAr: Record<string, string> = { watch: "مراقبة", moderate: "متوسط", urgent: "عاجل" };

export const findingLabelAr: Record<string, string> = { confirmed: "مؤكد", likely: "مرجح", unknown: "غير معروف" };

export const claimLabelAr: Record<string, string> = {
  confirmed: "موثّق",
  oral_account: "رواية شفهية",
  interpretation: "تفسير",
  unknown: "غير موثّق",
};

export const stageAr: Record<string, string> = {
  planning: "نجهّز الخطوات",
  identifying: "نتعرّف على الواجهة",
  answered: "شكرًا، نكمل",
  monitoring: "نقارن صورتك بالصورة المرجعية",
  verifying: "نتحقق من النتائج",
  guiding: "نحضّر لك الحكاية",
};

export const retakeAr: Record<string, string> = {
  blurry: "الصورة غير واضحة. ثبّت الجوال وصوّر مرة أخرى.",
  too_dark: "الصورة مظلمة جدًا. صوّر في إضاءة أفضل.",
  too_bright: "الصورة ساطعة جدًا. تجنّب الشمس المباشرة.",
  wrong_angle: "زاوية التصوير تختلف عن الصورة المرجعية. طابق الإطار وأعد التصوير.",
  lighting: "قد يكون ما ظهر ظلًا. صوّر في وقت آخر من اليوم.",
  unclear_change: "التغير غير واضح. اقترب قليلًا وأعد التصوير.",
};

export const confidenceAr: Record<string, string> = { low: "منخفضة", medium: "متوسطة", high: "عالية" };

export const cellSourceAr: Record<string, string> = { model: "النموذج", expert: "المختص" };

export const mapStatusAr: Record<string, string> = { draft: "مسودة", approved: "معتمد" };

export const detectorStatusAr: Record<string, string> = {
  ok: "حلّله النموذج",
  failed: "تعذر التحليل الآلي، يلزم التحديد اليدوي",
  manual: "تحديد يدوي",
};

export const changeKindAr: Record<string, string> = {
  new: "تلف جديد",
  worse: "ازداد سوءًا",
  retyped: "تغيّر نوعه",
  improved: "تحسّن",
  resolved: "لم يعد ظاهرًا",
};
