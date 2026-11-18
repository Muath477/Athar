import { describe, expect, it } from "vitest";
import {
  MAX_FILES,
  MAX_PHOTO_BYTES,
  type Message,
  checkFiles,
  elementMeasureAr,
  readEvents,
  skillStepAr,
  toolResultAr,
} from "@/lib/assistant";

function file(name: string, type: string, size = 1000): File {
  return new File([new Uint8Array(size)], name, { type });
}

function toolMessage(overrides: Partial<Message>): Message {
  return {
    id: "m",
    role: "tool",
    text: "",
    skill: null,
    skill_title: null,
    tool: "analyse_photo",
    data: { ok: true },
    created_at: "2026-11-18T08:00:00Z",
    attachments: [],
    action: null,
    ...overrides,
  };
}

const element = {
  id: "E1",
  damage_type: "crack",
  severity: "urgent" as const,
  confidence: "low" as const,
  damage_class: null,
  location: "B2",
  area_m2: null,
  length_m: null,
  count: null,
  needs_review: true,
};

describe("reply stream", () => {
  it("reads complete events and keeps the unfinished tail", () => {
    const chunk =
      'event: skill\r\ndata: {"name":"wall-photo-inspection","title_ar":"فحص صورة جدار"}\r\n\r\n' +
      'event: tool_call\r\ndata: {"tool":"analyse_photo"}\r\n\r\nevent: do';
    const { events, rest } = readEvents(chunk);
    expect(events).toEqual([
      { event: "skill", data: { name: "wall-photo-inspection", title_ar: "فحص صورة جدار" } },
      { event: "tool_call", data: { tool: "analyse_photo" } },
    ]);
    expect(rest).toBe("event: do");
    expect(readEvents(`${rest}ne\r\ndata: {}\r\n\r\n`).events).toEqual([{ event: "done", data: {} }]);
  });

  it("ignores keep-alive comments", () => {
    expect(readEvents(": ping\r\n\r\n").events).toEqual([]);
  });
});

describe("timeline labels", () => {
  it("names the chosen skill", () => {
    expect(skillStepAr("فحص صورة جدار")).toBe("اختار مهارة: فحص صورة جدار");
  });

  it("counts elements found in a photo with Arabic plurals", () => {
    const three = toolMessage({ data: { ok: true, elements: [element, { ...element, id: "E2" }, { ...element, id: "E3" }] } });
    expect(toolResultAr(three)).toBe("حلّل الصورة: ٣ عناصر");
    expect(toolResultAr(toolMessage({ data: { ok: true, elements: [] } }))).toBe("حلّل الصورة: لا عناصر");
  });

  it("marks failures and pending sends", () => {
    expect(toolResultAr(toolMessage({ data: { ok: false } }))).toBe("حلّل الصورة: تعذّر");
    const pending = toolMessage({
      tool: "send_report",
      action: { id: "a", kind: "send_report", status: "pending", file_name: "f.pdf", note_ar: "", decided_at: null },
    });
    expect(toolResultAr(pending)).toBe("جهّز طلب الإرسال: بانتظار تأكيدك");
    expect(toolResultAr(toolMessage({ tool: "send_report", data: { ok: true, status: "confirmed", delivered: true } }))).toBe(
      "جهّز طلب الإرسال: أُرسل",
    );
  });
});

describe("attachments", () => {
  it("accepts photos and PDFs up to the limits", () => {
    const { accepted, problems } = checkFiles(
      [],
      [file("a.jpg", "image/jpeg"), file("b.pdf", "application/pdf"), file("c.txt", "text/plain"), file("d.png", "image/png", MAX_PHOTO_BYTES + 1)],
    );
    expect(accepted.map((f) => f.name)).toEqual(["a.jpg", "b.pdf"]);
    expect(problems.map((p) => p.name)).toEqual(["c.txt", "d.png"]);
  });

  it("stops at the per-message file limit", () => {
    const current = Array.from({ length: MAX_FILES - 1 }, (_, i) => file(`${i}.jpg`, "image/jpeg"));
    const { accepted, problems } = checkFiles(current, [file("x.jpg", "image/jpeg"), file("y.jpg", "image/jpeg")]);
    expect(accepted.map((f) => f.name)).toEqual(["x.jpg"]);
    expect(problems).toEqual([{ name: "y.jpg", reason: "الحد ٦ ملفات في الرسالة." }]);
  });

  it("formats element measurements only when the wall size is known", () => {
    expect(elementMeasureAr(element)).toBe("—");
    expect(elementMeasureAr({ ...element, length_m: 1.25 })).toBe("١٫٢٥ م");
    expect(elementMeasureAr({ ...element, area_m2: 2 })).toBe("٢ م²");
  });
});
