import { type Permission, type Role, apiUrl, request } from "@/lib/api";
import type { Forms } from "@/lib/plural";

export type ManagedUser = {
  id: string;
  email: string;
  display_name: string;
  role: Role;
  site_ids: string[];
  is_active: boolean;
  must_change_password: boolean;
  last_login_at: string | null;
  created_at: string;
};

export type RoleMatrixRow = { role: Role; permissions: Permission[] };

export type AuditEntry = {
  id: string;
  at: string;
  actor_id: string | null;
  actor_email: string | null;
  action: string;
  target_type: string;
  target_id: string;
  details: Record<string, unknown>;
  request_id: string | null;
};

export type AuditPage = { entries: AuditEntry[]; total: number; page: number; page_size: number };

export type AuditFilters = { actor: string; action: string; target_type: string; from: string; to: string };

export const EMPTY_FILTERS: AuditFilters = { actor: "", action: "", target_type: "", from: "", to: "" };

export const permissionAr: Record<Permission, string> = {
  read: "الاطلاع على المواقع والمخططات",
  survey: "تصوير الجدران وإنشاء المخططات",
  review: "مراجعة المخططات واعتمادها",
  manage_site: "إدارة الموقع وتصاريح التصوير",
  manage_devices: "إدارة الكاميرات والأجهزة",
  export: "تصدير التقارير والجداول",
  assistant: "استخدام مساعد أثر",
  manage_models: "إدارة نماذج التحليل",
  read_audit: "قراءة سجل التدقيق",
  administer: "إدارة الحسابات والصلاحيات",
};

const ACTION_AR: Record<string, string> = {
  login: "تسجيل دخول",
  "map.create": "إنشاء مخطط تلف",
  "map.correct": "تصحيح خلايا مخطط",
  "map.edit_elements": "تعديل عناصر مخطط",
  "map.field_inspection": "تسجيل فحص ميداني",
  "map.approve": "اعتماد مخطط",
  "site.field_photography": "تغيير تصريح التصوير الميداني",
  "finding.confirm": "تأكيد ملاحظة",
  "finding.correct": "تصحيح ملاحظة",
  "finding.reject": "رفض ملاحظة",
  "passport.delete": "حذف جواز زائر وصوره",
  "mission.create": "فتح مهمة تصوير",
  "watch.scan": "طلب رصد فضائي",
  "watch.acknowledge": "الاطلاع على تنبيه فضائي",
  "watch.ground_check": "طلب تحقق ميداني",
  "user.create": "إنشاء حساب",
  "user.role": "تغيير دور حساب",
  "user.sites": "تحديد مواقع حساب",
  "user.deactivate": "إيقاف حساب",
  "user.reactivate": "إعادة تفعيل حساب",
  "user.password_reset": "تعيين كلمة مرور مؤقتة",
  "user.password_change": "تغيير كلمة المرور",
  "retention.purge": "حذف صور انتهت مدة حفظها",
  "notice.map_urgent": "إشعار بتلف عاجل",
  "notice.approval_overdue": "تذكير باعتماد متأخر",
};

export const ACTION_GROUPS: { prefix: string; label: string }[] = [
  { prefix: "map.", label: "المخططات" },
  { prefix: "finding.", label: "مراجعة الملاحظات" },
  { prefix: "user.", label: "الحسابات" },
  { prefix: "site.", label: "الموقع" },
  { prefix: "watch.", label: "الرصد من الفضاء" },
  { prefix: "login", label: "تسجيل الدخول" },
  { prefix: "passport.", label: "جوازات الزوار" },
  { prefix: "retention.", label: "حفظ الصور" },
  { prefix: "notice.", label: "الإشعارات" },
];

export const TARGET_TYPES: { value: string; label: string }[] = [
  { value: "damage_map", label: "مخطط تلف" },
  { value: "user", label: "حساب" },
  { value: "site", label: "موقع" },
  { value: "finding", label: "ملاحظة" },
  { value: "site_scan", label: "رصد فضائي" },
  { value: "mission", label: "مهمة تصوير" },
  { value: "passport", label: "جواز زائر" },
  { value: "observation", label: "صورة زائر" },
];

export function auditActionAr(action: string): string {
  return ACTION_AR[action] ?? action;
}

export function auditQuery(filters: AuditFilters, page?: number): string {
  const params = new URLSearchParams();
  if (filters.actor.trim()) params.set("actor", filters.actor.trim());
  if (filters.action) params.set("action", filters.action);
  if (filters.target_type) params.set("target_type", filters.target_type);
  if (filters.from) params.set("from", startOfDay(filters.from));
  if (filters.to) params.set("to", startOfDay(filters.to, 1));
  if (page) params.set("page", String(page));
  const query = params.toString();
  return query ? `?${query}` : "";
}

function startOfDay(day: string, addDays = 0): string {
  const date = new Date(`${day}T00:00:00+03:00`);
  date.setUTCDate(date.getUTCDate() + addDays);
  return date.toISOString();
}

export function auditCsvUrl(filters: AuditFilters): string {
  return apiUrl(`/admin/audit.csv${auditQuery(filters)}`);
}

export const listAudit = (filters: AuditFilters, page: number) =>
  request<AuditPage>(`/admin/audit${auditQuery(filters, page)}`);

export const listUsers = () => request<ManagedUser[]>("/admin/users");

export const roleMatrix = () => request<RoleMatrixRow[]>("/auth/roles");

export type NewUser = { email: string; display_name: string; role: Role; password: string; site_ids: string[] };

export const createUser = (user: NewUser) =>
  request<ManagedUser>("/admin/users", { method: "POST", body: JSON.stringify(user) });

export const changeRole = (id: string, role: Role) =>
  request<ManagedUser>(`/admin/users/${id}/role`, { method: "POST", body: JSON.stringify({ role }) });

export const assignSites = (id: string, siteIds: string[]) =>
  request<ManagedUser>(`/admin/users/${id}/sites`, { method: "POST", body: JSON.stringify({ site_ids: siteIds }) });

export const setActive = (id: string, active: boolean) =>
  request<ManagedUser>(`/admin/users/${id}/active`, { method: "POST", body: JSON.stringify({ active }) });

export const resetPassword = (id: string, temporaryPassword: string) =>
  request<ManagedUser>(`/admin/users/${id}/password`, {
    method: "POST",
    body: JSON.stringify({ temporary_password: temporaryPassword }),
  });

export const changeOwnPassword = (current: string, next: string) =>
  request<void>("/auth/password", {
    method: "POST",
    body: JSON.stringify({ current_password: current, new_password: next }),
  });

export const MIN_PASSWORD_LENGTH = 12;

export const auditEntries: Forms = {
  zero: "لا سجلات",
  one: "سجل واحد",
  two: "سجلان",
  few: "سجلات",
  many: "سجلًا",
  hundred: "سجل",
};

export function seesEverySite(role: Role): boolean {
  return role === "admin" || role === "authority";
}
