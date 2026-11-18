"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { PageSkeleton, RetryAlert } from "@/app/_components/page-status";
import { ApiError, type Site, can, request } from "@/lib/api";
import {
  type Conversation,
  type ConversationSummary,
  type Message,
  type ReplyEvent,
  analyseAttachment,
  createConversation,
  decideAction,
  getConversation,
  listConversations,
  postMessage,
  skillStepAr,
  streamReply,
  toolLabelAr,
  toolResultAr,
} from "@/lib/assistant";
import { useMeState } from "@/lib/use-me";
import { Composer } from "./composer";
import { ConversationList } from "./conversation-list";
import { type FacadeOption, MessageLog } from "./message-log";
import type { ReplyProgress, Step } from "./reply-progress";

export function AssistantView() {
  const { me, error: meError, retry: retryMe } = useMeState();
  const router = useRouter();
  const params = useSearchParams();
  const activeId = params.get("c");
  const [conversations, setConversations] = useState<ConversationSummary[] | null>(null);
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [facades, setFacades] = useState<FacadeOption[]>([]);
  const [progress, setProgress] = useState<ReplyProgress | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [sendError, setSendError] = useState<string | null>(null);
  const replyAbort = useRef<AbortController | null>(null);
  const allowed = can(me, "assistant");

  const loadList = useCallback(
    () =>
      listConversations().then(setConversations, (e) =>
        setLoadError(e instanceof ApiError ? e.message : "تعذر تحميل المحادثات."),
      ),
    [],
  );

  useEffect(() => {
    if (!allowed) return;
    loadList();
    request<Site[]>("/sites").then(
      (sites) => setFacades(sites.flatMap((s) => s.facades.map((f) => ({ id: f.id, label: `${s.name_ar} · ${f.name_ar}` })))),
      () => setFacades([]),
    );
  }, [allowed, loadList]);

  useEffect(() => {
    if (!allowed || !activeId || conversation?.id === activeId) return;
    let cancelled = false;
    getConversation(activeId).then(
      (loaded) => {
        if (!cancelled) setConversation(loaded);
      },
      (e) => {
        if (!cancelled) setLoadError(e instanceof ApiError ? e.message : "تعذر فتح المحادثة.");
      },
    );
    return () => {
      cancelled = true;
    };
  }, [allowed, activeId, conversation?.id]);

  useEffect(() => () => replyAbort.current?.abort(), []);

  function append(message: Message) {
    setConversation((current) => (current ? { ...current, messages: [...current.messages, message] } : current));
  }

  function settleAction(actionId: string, status: "confirmed" | "cancelled") {
    setConversation((current) =>
      current
        ? {
            ...current,
            messages: current.messages.map((m) => (m.action?.id === actionId ? { ...m, action: { ...m.action, status } } : m)),
          }
        : current,
    );
  }

  function onReplyEvent(event: ReplyEvent) {
    switch (event.event) {
      case "skill":
        setProgress((p) => p && { ...p, skill: event.data.title_ar, steps: [...p.steps, newStep(p.steps, skillStepAr(event.data.title_ar), "done")] });
        break;
      case "step":
        setProgress((p) => p && { ...p, thinking: true });
        break;
      case "tool_call":
        setProgress((p) => p && { ...p, thinking: false, steps: [...p.steps, newStep(p.steps, toolLabelAr[event.data.tool], "running")] });
        break;
      case "tool_result":
        append(event.data.message);
        setProgress((p) => p && { ...p, steps: finishLastStep(p.steps, event.data.message) });
        break;
      case "message":
        append(event.data.message);
        break;
      case "error":
        setSendError(event.data.detail_ar);
        break;
    }
  }

  async function runReply(conversationId: string) {
    const controller = new AbortController();
    replyAbort.current = controller;
    setProgress({ skill: null, thinking: true, steps: [] });
    try {
      await streamReply(conversationId, onReplyEvent, controller.signal);
    } catch (e) {
      if (!controller.signal.aborted) {
        setSendError(e instanceof ApiError ? e.message : "انقطع الاتصال أثناء رد المساعد. حدّث الصفحة لترى ما حُفظ.");
      }
    } finally {
      setProgress(null);
      loadList();
    }
  }

  async function send(text: string, files: File[]): Promise<boolean> {
    setSendError(null);
    try {
      let target = conversation;
      if (!target) {
        target = await createConversation();
        setConversation(target);
        router.replace(`/dashboard/assistant?c=${target.id}`);
      }
      append(await postMessage(target.id, text, files));
      void runReply(target.id);
      return true;
    } catch (e) {
      setSendError(e instanceof ApiError ? e.message : "تعذر إرسال الرسالة. تحقق من الاتصال وأعد المحاولة.");
      return false;
    }
  }

  async function analyse(attachmentId: string, facadeId: string | null) {
    if (!conversation) return;
    setSendError(null);
    try {
      append(await analyseAttachment(conversation.id, attachmentId, facadeId));
    } catch (e) {
      setSendError(e instanceof ApiError ? e.message : "تعذر تحليل الصورة. أعد المحاولة.");
    }
  }

  async function decide(actionId: string, confirm: boolean) {
    setSendError(null);
    try {
      append(await decideAction(actionId, confirm));
      settleAction(actionId, confirm ? "confirmed" : "cancelled");
    } catch (e) {
      setSendError(e instanceof ApiError ? e.message : "تعذر تنفيذ طلبك. أعد المحاولة.");
    }
  }

  function startNew() {
    replyAbort.current?.abort();
    setConversation(null);
    setSendError(null);
    router.replace("/dashboard/assistant");
  }

  if (meError) return <RetryAlert message={meError} onRetry={retryMe} />;
  if (!me) return <AssistantSkeleton />;
  if (!allowed) {
    return (
      <p role="alert" className="rounded-sm bg-white p-4">
        لا تملك صلاحية استخدام مساعد أثر. اطلبها من مسؤول النظام.
      </p>
    );
  }
  if (loadError) {
    return (
      <RetryAlert
        message={loadError}
        onRetry={() => {
          setLoadError(null);
          setConversation(null);
          loadList();
        }}
      />
    );
  }

  const busy = progress !== null;
  const opening = activeId !== null && conversation?.id !== activeId;

  return (
    <div className="flex flex-col gap-4">
      <header className="flex flex-col gap-1">
        <h1 className="text-3xl font-bold leading-snug">مساعد أثر</h1>
        <p className="max-w-3xl text-mud">
          أرفق صور الجدران أو صور الدرون أو تقارير الفحص القديمة، واطلب الفحص أو ملف التدقيق. كل ما يخرجه المساعد مسودة
          لا تُعتمد إلا بمراجعة المختص، ولا يُرسل شيء إلا بتأكيدك.
        </p>
      </header>

      <div className="grid gap-4 lg:grid-cols-[16rem_minmax(0,1fr)]">
        <ConversationList conversations={conversations} activeId={activeId} onStartNew={startNew} disabled={busy} />
        <section aria-label="المحادثة" className="flex min-w-0 flex-col gap-3 rounded-sm bg-white/60 p-3">
          {opening ? (
            <PageSkeleton />
          ) : (
            <MessageLog
              messages={conversation?.messages ?? []}
              progress={progress}
              facades={facades}
              busy={busy}
              onAnalyse={analyse}
              onDecide={decide}
            />
          )}
          {sendError && (
            <p role="alert" className="rounded-sm border border-urgent/40 bg-urgent/10 p-3 text-sm">
              {sendError}
            </p>
          )}
          <Composer busy={busy || opening} onSend={send} />
        </section>
      </div>
    </div>
  );
}

function newStep(steps: Step[], label: string, state: Step["state"]): Step {
  return { key: String(steps.length), label, state };
}

function finishLastStep(steps: Step[], message: Message): Step[] {
  const index = steps.findLastIndex((s) => s.state === "running");
  if (index < 0) return steps;
  const state = message.data.ok === false ? "failed" : "done";
  return steps.map((s, i) => (i === index ? { ...s, label: toolResultAr(message), state } : s));
}

export function AssistantSkeleton() {
  return (
    <PageSkeleton>
      <div className="h-9 w-56 rounded-sm bg-clay/25" />
      <div className="grid gap-4 lg:grid-cols-[16rem_minmax(0,1fr)]">
        <div className="h-64 rounded-sm bg-clay/60" />
        <div className="h-96 rounded-sm bg-clay/60" />
      </div>
    </PageSkeleton>
  );
}
