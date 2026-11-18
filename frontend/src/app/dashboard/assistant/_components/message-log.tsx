"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useId, useRef, useState } from "react";
import { type Attachment, type ElementRow, type Message, type PendingAction, elementMeasureAr, toolResultAr } from "@/lib/assistant";
import { classAr } from "@/lib/elements";
import { confidenceAr, damageTypeAr, severityAr } from "@/lib/labels";
import { type ReplyProgress, ReplyTimeline } from "./reply-progress";

export type FacadeOption = { id: string; label: string };

type Handlers = {
  facades: FacadeOption[];
  busy: boolean;
  onAnalyse: (attachmentId: string, facadeId: string | null) => Promise<void>;
  onDecide: (actionId: string, confirm: boolean) => Promise<void>;
};

const SECONDARY_CLASS = "min-h-11 rounded-full border border-ink/30 px-4 text-sm hover:bg-ink hover:text-sand disabled:opacity-50";

export function MessageLog({
  messages,
  progress,
  ...handlers
}: { messages: Message[]; progress: ReplyProgress | null } & Handlers) {
  const end = useRef<HTMLDivElement>(null);
  const steps = progress?.steps.length ?? 0;

  useEffect(() => {
    end.current?.scrollIntoView({ block: "nearest" });
  }, [messages.length, steps]);

  return (
    <div role="log" aria-label="رسائل المحادثة" className="flex max-h-[65dvh] min-h-64 flex-col gap-3 overflow-y-auto p-1">
      {messages.length === 0 && !progress && (
        <p className="m-auto max-w-md text-center text-mud">
          ابدأ بإرفاق صورة جدار واكتب مثلًا: «حلّل صورة الواجهة الشمالية واكتب ملف التدقيق».
        </p>
      )}
      {messages.map((message) => (
        <MessageItem key={message.id} message={message} {...handlers} />
      ))}
      {progress && <ReplyTimeline progress={progress} />}
      <div ref={end} />
    </div>
  );
}

function MessageItem({ message, ...handlers }: { message: Message } & Handlers) {
  if (message.role === "user") return <UserMessage message={message} {...handlers} />;
  if (message.role === "tool") return <ToolMessage message={message} {...handlers} />;
  return <AgentMessage message={message} />;
}

function UserMessage({ message, ...handlers }: { message: Message } & Handlers) {
  return (
    <article aria-label="رسالتك" className="ms-auto flex max-w-[85%] flex-col gap-2 rounded-xl bg-ink/10 p-3">
      {message.text && <p className="whitespace-pre-line">{message.text}</p>}
      {message.attachments.length > 0 && (
        <ul aria-label="المرفقات" className="flex flex-wrap gap-3">
          {message.attachments.map((attachment) => (
            <li key={attachment.id} className="flex flex-col gap-2">
              {attachment.kind === "photo" ? (
                <PhotoAttachment attachment={attachment} {...handlers} />
              ) : (
                <FileLink attachment={attachment} />
              )}
            </li>
          ))}
        </ul>
      )}
    </article>
  );
}

function PhotoAttachment({ attachment, facades, busy, onAnalyse }: { attachment: Attachment } & Handlers) {
  const selectId = useId();
  const [facadeId, setFacadeId] = useState("");
  const [analysing, setAnalysing] = useState(false);

  async function analyse() {
    setAnalysing(true);
    await onAnalyse(attachment.id, facadeId || null);
    setAnalysing(false);
  }

  return (
    <>
      <a href={attachment.url} target="_blank" rel="noreferrer" className="block w-40">
        <Image
          src={attachment.url}
          alt={`صورة مرفقة: ${attachment.file_name}`}
          width={160}
          height={120}
          unoptimized
          className="h-28 w-40 rounded-lg object-cover"
        />
      </a>
      <div className="flex w-40 flex-col gap-1 text-sm">
        <label htmlFor={selectId} className="text-mud">
          الواجهة (اختياري)
        </label>
        <select
          id={selectId}
          value={facadeId}
          onChange={(e) => setFacadeId(e.target.value)}
          className="min-h-11 rounded-lg border border-mud/60 bg-white px-2"
        >
          <option value="">دون حفظ مخطط</option>
          {facades.map((f) => (
            <option key={f.id} value={f.id}>
              {f.label}
            </option>
          ))}
        </select>
        <button type="button" onClick={analyse} disabled={busy || analysing} className={SECONDARY_CLASS}>
          {analysing ? "يحلّل…" : "حلّل الصورة"}
        </button>
      </div>
    </>
  );
}

function FileLink({ attachment }: { attachment: Attachment }) {
  const label = attachment.kind === "audit_report" ? "نزّل ملف التدقيق" : "افتح المستند";
  return (
    <a
      href={attachment.url}
      download={attachment.file_name}
      className="inline-flex min-h-11 items-center gap-2 rounded-lg border border-mud/60 bg-white px-3 text-sm hover:bg-sand"
    >
      <span className="font-bold">{label}</span>
      <bdi className="text-mud">{attachment.file_name}</bdi>
    </a>
  );
}

function ToolMessage({ message, onDecide }: { message: Message } & Handlers) {
  const failed = message.data.ok === false;
  const elements = message.data.elements ?? [];
  return (
    <article
      aria-label={toolResultAr(message)}
      className={`flex flex-col gap-2 rounded-xl border p-3 text-sm ${failed ? "border-urgent/40 bg-urgent/5" : "border-clay/40 bg-white/75"}`}
    >
      <p className="font-bold">{toolResultAr(message)}</p>
      <p className={failed ? "text-urgent" : "text-mud"}>{message.text}</p>
      {elements.length > 0 && <ElementsTable rows={elements} wallName={message.data.wall_name ?? ""} />}
      {message.data.map_url && (
        <Link href={message.data.map_url} className="self-start font-bold text-sadu underline underline-offset-4">
          افتح مسودة المخطط للمراجعة
        </Link>
      )}
      {message.attachments.map((attachment) => (
        <FileLink key={attachment.id} attachment={attachment} />
      ))}
      {message.action && <ActionCard action={message.action} onDecide={onDecide} />}
    </article>
  );
}

function ElementsTable({ rows, wallName }: { rows: ElementRow[]; wallName: string }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[36rem] border-collapse text-start">
        <caption className="pb-1 text-start text-mud">
          عناصر التلف في <bdi>{wallName}</bdi>
        </caption>
        <thead>
          <tr className="bg-sand">
            {["العنصر", "النوع", "الموقع", "القياس", "الفئة", "الشدة", "الثقة"].map((heading) => (
              <th key={heading} scope="col" className="px-2 py-1 text-start">
                {heading}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id} className="border-b border-clay/30">
              <td className="px-2 py-1">
                <bdi>{row.id}</bdi>
                {(row.needs_review || row.severity === "urgent") && <span className="ms-1 text-urgent">· زيارة ميدانية</span>}
              </td>
              <td className="px-2 py-1">{damageTypeAr[row.damage_type] ?? row.damage_type}</td>
              <td className="px-2 py-1">
                <bdi>{row.location}</bdi>
              </td>
              <td className="px-2 py-1 tabular-nums">{elementMeasureAr(row)}</td>
              <td className="px-2 py-1">{row.damage_class ? (classAr[row.damage_class] ?? row.damage_class) : "—"}</td>
              <td className={`px-2 py-1 ${row.severity === "urgent" ? "font-bold text-urgent" : ""}`}>{severityAr[row.severity]}</td>
              <td className="px-2 py-1">{confidenceAr[row.confidence]}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ActionCard({ action, onDecide }: { action: PendingAction; onDecide: Handlers["onDecide"] }) {
  const [deciding, setDeciding] = useState(false);

  async function decide(confirm: boolean) {
    setDeciding(true);
    await onDecide(action.id, confirm);
    setDeciding(false);
  }

  if (action.status !== "pending") {
    return (
      <p role="status" className="font-bold">
        {action.status === "confirmed" ? "أكدتَ الإرسال." : "ألغيتَ الإرسال."}
      </p>
    );
  }
  return (
    <div className="flex flex-col gap-2 rounded-lg border border-sadu/50 bg-sand/60 p-3">
      <p>
        إرسال <bdi className="font-bold">{action.file_name}</bdi> إلى المختصين ينتظر تأكيدك. سيصلهم رابط الملف لمراجعته
        واعتماده، ولا يمكن سحب الإرسال بعد تأكيده.
      </p>
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => decide(true)}
          disabled={deciding}
          className="min-h-11 rounded-full bg-sadu px-5 font-bold text-sand hover:bg-ink disabled:opacity-50"
        >
          أكّد الإرسال
        </button>
        <button type="button" onClick={() => decide(false)} disabled={deciding} className={SECONDARY_CLASS}>
          ألغِ الإرسال
        </button>
      </div>
    </div>
  );
}

function AgentMessage({ message }: { message: Message }) {
  const unavailable = message.data.llm_available === false;
  return (
    <article
      aria-label="رد المساعد"
      className={`me-auto flex max-w-[85%] flex-col gap-1 rounded-xl p-3 ${unavailable ? "border border-urgent/40 bg-urgent/10" : "bg-white"}`}
    >
      {message.skill_title && (
        <p className="text-sm text-mud">
          المهارة: <bdi>{message.skill_title}</bdi>
        </p>
      )}
      <p className="whitespace-pre-line">{message.text}</p>
    </article>
  );
}
