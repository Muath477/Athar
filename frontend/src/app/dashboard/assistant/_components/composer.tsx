"use client";

import Image from "next/image";
import { type DragEvent, type FormEvent, type KeyboardEvent, useEffect, useRef, useState } from "react";
import { ACCEPTED_TYPES, type FileProblem, PHOTO_TYPES, checkFiles } from "@/lib/assistant";
import { buttonVariants } from "@/components/ui/button";

type Draft = { file: File; preview: string | null };

export function Composer({ busy, onSend }: { busy: boolean; onSend: (text: string, files: File[]) => Promise<boolean> }) {
  const [text, setText] = useState("");
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [problems, setProblems] = useState<FileProblem[]>([]);
  const [dropping, setDropping] = useState(false);
  const [sending, setSending] = useState(false);
  const textArea = useRef<HTMLTextAreaElement>(null);
  const previews = useRef<string[]>([]);

  useEffect(() => {
    previews.current = drafts.flatMap((d) => (d.preview ? [d.preview] : []));
  }, [drafts]);

  useEffect(() => () => previews.current.forEach((url) => URL.revokeObjectURL(url)), []);

  function addFiles(list: FileList | null) {
    if (!list) return;
    const { accepted, problems: found } = checkFiles(
      drafts.map((d) => d.file),
      Array.from(list),
    );
    setProblems(found);
    setDrafts((current) => [
      ...current,
      ...accepted.map((file) => ({ file, preview: PHOTO_TYPES.includes(file.type) ? URL.createObjectURL(file) : null })),
    ]);
  }

  function removeDraft(index: number) {
    const removed = drafts[index];
    if (removed.preview) URL.revokeObjectURL(removed.preview);
    setDrafts((current) => current.filter((_, i) => i !== index));
    setProblems([]);
    textArea.current?.focus();
  }

  function onDrop(event: DragEvent<HTMLFormElement>) {
    event.preventDefault();
    setDropping(false);
    if (!busy) addFiles(event.dataTransfer.files);
  }

  async function submit(event?: FormEvent) {
    event?.preventDefault();
    if (busy || sending || (!text.trim() && drafts.length === 0)) return;
    setSending(true);
    const sent = await onSend(text.trim(), drafts.map((d) => d.file));
    setSending(false);
    if (!sent) return;
    drafts.forEach((d) => d.preview && URL.revokeObjectURL(d.preview));
    setDrafts([]);
    setText("");
    setProblems([]);
    textArea.current?.focus();
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      void submit();
    }
  }

  const empty = !text.trim() && drafts.length === 0;

  return (
    <form
      onSubmit={submit}
      onDragOver={(e) => {
        e.preventDefault();
        setDropping(true);
      }}
      onDragLeave={() => setDropping(false)}
      onDrop={onDrop}
      aria-label="اكتب رسالتك"
      className={`flex flex-col gap-2 rounded-sm border-2 p-2 transition-colors ${
        dropping ? "border-dashed border-sadu bg-white" : "border-transparent"
      }`}
    >
      <label htmlFor="assistant-message" className="sr-only">
        رسالتك إلى المساعد
      </label>
      <textarea
        id="assistant-message"
        ref={textArea}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={onKeyDown}
        rows={3}
        maxLength={4000}
        placeholder="مثل: حلّل صورة الواجهة الشمالية واكتب ملف التدقيق"
        aria-describedby="assistant-message-hint"
        className="min-h-11 w-full resize-y rounded-sm border border-mud/60 bg-white p-3 text-base"
      />
      <p id="assistant-message-hint" className="text-sm text-mud">
        Enter للإرسال، وShift+Enter لسطر جديد. يمكنك سحب الصور أو ملفات PDF وإفلاتها هنا.
      </p>

      {drafts.length > 0 && (
        <ul aria-label="مرفقات الرسالة" className="flex flex-wrap gap-2">
          {drafts.map((draft, index) => (
            <li key={`${draft.file.name}-${index}`} className="flex items-center gap-2 rounded-sm bg-white p-1.5 text-sm">
              {draft.preview ? (
                <Image src={draft.preview} alt="" width={48} height={48} unoptimized className="size-12 rounded object-cover" />
              ) : (
                <span aria-hidden="true" className="flex size-12 items-center justify-center rounded bg-sand font-bold text-mud">
                  PDF
                </span>
              )}
              <bdi className="max-w-36 truncate">{draft.file.name}</bdi>
              <button
                type="button"
                onClick={() => removeDraft(index)}
                aria-label={`أزل ${draft.file.name}`}
                className={buttonVariants({ variant: "ghost", size: "icon" })}
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}

      {problems.length > 0 && (
        <ul role="alert" className="flex flex-col gap-1 text-sm text-urgent">
          {problems.map((p) => (
            <li key={p.name}>
              <bdi>{p.name}</bdi>: {p.reason}
            </li>
          ))}
        </ul>
      )}

      <div className="flex flex-wrap items-center justify-between gap-2">
        <label className={buttonVariants({ variant: "outline", className: "cursor-pointer has-[:focus-visible]:outline has-[:focus-visible]:outline-[3px] has-[:focus-visible]:outline-sadu" })}>
          أرفق صورًا أو PDF
          <input
            type="file"
            multiple
            accept={ACCEPTED_TYPES}
            disabled={busy}
            className="sr-only"
            onChange={(e) => {
              addFiles(e.target.files);
              e.target.value = "";
            }}
          />
        </label>
        <button
          type="submit"
          disabled={busy || sending || empty}
          className={buttonVariants()}
        >
          {busy ? "المساعد يرد…" : "أرسل"}
        </button>
      </div>
    </form>
  );
}
