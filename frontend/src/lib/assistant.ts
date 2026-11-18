import { ApiError, csrfToken, request } from "@/lib/api";
import { countAr, elements as elementForms, type Forms } from "@/lib/plural";

const BASE = "/api/v1";

export const MAX_FILES = 6;
export const MAX_PHOTO_BYTES = 8 * 1024 * 1024;
export const MAX_PDF_BYTES = 10 * 1024 * 1024;
export const PHOTO_TYPES = ["image/jpeg", "image/png"];
export const PDF_TYPE = "application/pdf";
export const ACCEPTED_TYPES = [...PHOTO_TYPES, PDF_TYPE].join(",");

export type ToolName =
  | "analyse_photo"
  | "get_site_condition"
  | "list_sites"
  | "get_map"
  | "get_watch_status"
  | "find_treatments"
  | "draft_audit_report"
  | "send_report";

export type Attachment = {
  id: string;
  kind: "photo" | "document" | "audit_report";
  file_name: string;
  media_type: string;
  size_bytes: number;
  url: string;
};

export type PendingAction = {
  id: string;
  kind: "send_report";
  status: "pending" | "confirmed" | "cancelled";
  file_name: string;
  note_ar: string;
  decided_at: string | null;
};

export type ElementRow = {
  id: string;
  damage_type: string;
  severity: "watch" | "moderate" | "urgent";
  confidence: "low" | "medium" | "high";
  damage_class: string | null;
  location: string;
  area_m2: number | null;
  length_m: number | null;
  count: number | null;
  needs_review: boolean;
};

export type MessageData = {
  ok?: boolean;
  llm_available?: boolean;
  map_url?: string | null;
  wall_name?: string;
  measured?: boolean;
  elements?: ElementRow[];
  items?: { code: string; title_ar: string; damage_type: string; severity: string; specialist_required: boolean }[];
  sites?: { id: string; name_ar: string; facades: { id: string; name_ar: string }[] }[];
  status?: string;
  delivered?: boolean | null;
  [key: string]: unknown;
};

export type Message = {
  id: string;
  role: "user" | "agent" | "tool";
  text: string;
  skill: string | null;
  skill_title: string | null;
  tool: ToolName | null;
  data: MessageData;
  created_at: string;
  attachments: Attachment[];
  action: PendingAction | null;
};

export type ConversationSummary = { id: string; title: string; created_at: string; updated_at: string };

export type Conversation = ConversationSummary & { messages: Message[] };

export type ReplyEvent =
  | { event: "skill"; data: { name: string; title_ar: string } }
  | { event: "step"; data: { step: number } }
  | { event: "tool_call"; data: { tool: ToolName } }
  | { event: "tool_result"; data: { message: Message } }
  | { event: "message"; data: { message: Message } }
  | { event: "error"; data: { code: string; detail_ar: string } }
  | { event: "done"; data: Record<string, never> };

export const toolLabelAr: Record<ToolName, string> = {
  analyse_photo: "حلّل الصورة",
  get_site_condition: "قرأ حالة الموقع",
  list_sites: "عرض المواقع",
  get_map: "فتح المخطط",
  get_watch_status: "قرأ الرصد الفضائي",
  find_treatments: "بحث في دليل المعالجات",
  draft_audit_report: "صاغ ملف التدقيق",
  send_report: "جهّز طلب الإرسال",
};

const treatmentForms: Forms = {
  zero: "لا معالجات",
  one: "معالجة واحدة",
  two: "معالجتان",
  few: "معالجات",
  many: "معالجة",
  hundred: "معالجة",
};

const siteForms: Forms = { zero: "لا مواقع", one: "موقع واحد", two: "موقعان", few: "مواقع", many: "موقعًا", hundred: "موقع" };

export function skillStepAr(title: string): string {
  return `اختار مهارة: ${title}`;
}

export function toolResultAr(message: Message): string {
  const label = message.tool ? toolLabelAr[message.tool] : "أداة";
  if (message.data.ok === false) return `${label}: تعذّر`;
  switch (message.tool) {
    case "analyse_photo":
    case "get_map":
      return `${label}: ${countAr(message.data.elements?.length ?? 0, elementForms)}`;
    case "find_treatments":
      return `${label}: ${countAr(message.data.items?.length ?? 0, treatmentForms)}`;
    case "list_sites":
      return `${label}: ${countAr(message.data.sites?.length ?? 0, siteForms)}`;
    case "draft_audit_report":
      return `${label}: جاهز`;
    case "send_report":
      return `${label}: ${message.action ? "بانتظار تأكيدك" : sendOutcomeAr(message.data)}`;
    default:
      return label;
  }
}

function sendOutcomeAr(data: MessageData): string {
  if (data.status === "cancelled") return "أُلغي";
  return data.delivered ? "أُرسل" : "سُجّل دون قناة إرسال";
}

export type FileProblem = { name: string; reason: string };

export function checkFiles(current: File[], incoming: File[]): { accepted: File[]; problems: FileProblem[] } {
  const accepted: File[] = [];
  const problems: FileProblem[] = [];
  for (const file of incoming) {
    const isPhoto = PHOTO_TYPES.includes(file.type);
    const isPdf = file.type === PDF_TYPE;
    if (!isPhoto && !isPdf) problems.push({ name: file.name, reason: "الصيغ المقبولة JPEG وPNG وPDF فقط." });
    else if (isPhoto && file.size > MAX_PHOTO_BYTES) problems.push({ name: file.name, reason: `الصورة أكبر من ${megabytes(MAX_PHOTO_BYTES)} ميغابايت.` });
    else if (isPdf && file.size > MAX_PDF_BYTES) problems.push({ name: file.name, reason: `الملف أكبر من ${megabytes(MAX_PDF_BYTES)} ميغابايت.` });
    else if (current.length + accepted.length >= MAX_FILES) problems.push({ name: file.name, reason: `الحد ${MAX_FILES.toLocaleString("ar-SA")} ملفات في الرسالة.` });
    else accepted.push(file);
  }
  return { accepted, problems };
}

function megabytes(bytes: number): string {
  return (bytes / (1024 * 1024)).toLocaleString("ar-SA");
}

export function readEvents(buffer: string): { events: ReplyEvent[]; rest: string } {
  const blocks = buffer.split(/\r?\n\r?\n/);
  const rest = blocks.pop() ?? "";
  const events: ReplyEvent[] = [];
  for (const block of blocks) {
    let name = "";
    const data: string[] = [];
    for (const line of block.split(/\r?\n/)) {
      if (line.startsWith("event:")) name = line.slice(6).trim();
      else if (line.startsWith("data:")) data.push(line.slice(5).trimStart());
    }
    if (name) events.push({ event: name, data: data.length ? JSON.parse(data.join("\n")) : {} } as ReplyEvent);
  }
  return { events, rest };
}

export function listConversations(): Promise<ConversationSummary[]> {
  return request<ConversationSummary[]>("/assistant/conversations");
}

export function createConversation(): Promise<Conversation> {
  return request<Conversation>("/assistant/conversations", { method: "POST", body: JSON.stringify({}) });
}

export function getConversation(id: string): Promise<Conversation> {
  return request<Conversation>(`/assistant/conversations/${id}`);
}

export function postMessage(conversationId: string, text: string, files: File[]): Promise<Message> {
  const body = new FormData();
  body.append("text", text);
  for (const file of files) body.append("files", file);
  return request<Message>(`/assistant/conversations/${conversationId}/messages`, { method: "POST", body });
}

export function analyseAttachment(conversationId: string, attachmentId: string, facadeId: string | null): Promise<Message> {
  return request<Message>(`/assistant/conversations/${conversationId}/attachments/${attachmentId}/analyse`, {
    method: "POST",
    body: JSON.stringify({ facade_id: facadeId }),
  });
}

export function decideAction(actionId: string, confirm: boolean): Promise<Message> {
  return request<Message>(`/assistant/actions/${actionId}/${confirm ? "confirm" : "cancel"}`, { method: "POST" });
}

export async function streamReply(
  conversationId: string,
  onEvent: (event: ReplyEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const headers = new Headers({ Accept: "text/event-stream", "Accept-Language": "ar" });
  const csrf = csrfToken();
  if (csrf) headers.set("X-CSRF-Token", csrf);
  const response = await fetch(`${BASE}/assistant/conversations/${conversationId}/reply`, {
    method: "POST",
    headers,
    credentials: "same-origin",
    signal,
  });
  if (!response.ok || !response.body) {
    const problem = await response.json().catch(() => ({}));
    throw new ApiError(response.status, problem.code ?? "http_error", problem.detail ?? "تعذر بدء رد المساعد.");
  }
  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    const parsed = readEvents(buffer + value);
    buffer = parsed.rest;
    parsed.events.forEach(onEvent);
  }
  readEvents(`${buffer}\n\n`).events.forEach(onEvent);
}


export function elementMeasureAr(row: ElementRow): string {
  const format = (value: number) => value.toLocaleString("ar-SA", { maximumFractionDigits: 2 });
  if (row.count) return `${format(row.count)} نقطة`;
  if (row.length_m) return `${format(row.length_m)} م`;
  if (row.area_m2) return `${format(row.area_m2)} م²`;
  return "—";
}
