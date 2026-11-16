import { eventsUrl, type ObservationState, passportToken, request } from "@/lib/api";

const POLL_MS = 2000;
const FINAL = new Set(["done", "needs_retake", "failed"]);

/**
 * Follows an observation until it finishes. Reads the server-sent event stream with fetch,
 * because EventSource cannot send the passport header; falls back to polling if the stream breaks.
 */
export function followObservation(observationId: string, onState: (state: ObservationState) => void): () => void {
  const controller = new AbortController();
  let stopped = false;

  async function stream(): Promise<boolean> {
    const headers = new Headers({ Accept: "text/event-stream" });
    const token = passportToken();
    if (token) headers.set("X-Passport-Token", token);
    const response = await fetch(eventsUrl(observationId), { headers, signal: controller.signal });
    if (!response.ok || !response.body) return false;

    const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
    let buffer = "";
    for (;;) {
      const { value, done } = await reader.read();
      if (done) return true;
      buffer += value;
      const events = buffer.split(/\r?\n\r?\n/);
      buffer = events.pop() ?? "";
      for (const event of events) {
        const data = event
          .split(/\r?\n/)
          .filter((line) => line.startsWith("data:"))
          .map((line) => line.slice(5).trimStart())
          .join("\n");
        if (data) onState(JSON.parse(data) as ObservationState);
      }
    }
  }

  async function poll() {
    while (!stopped) {
      const state = await request<{ status: ObservationState["status"]; detail: ObservationState["detail"] }>(
        `/observations/${observationId}`,
      );
      onState(state);
      if (FINAL.has(state.status)) return;
      await new Promise((resolve) => setTimeout(resolve, POLL_MS));
    }
  }

  stream()
    .then((finished) => (finished ? undefined : poll()))
    .catch(() => (stopped ? undefined : poll()))
    .catch(() => undefined);

  return () => {
    stopped = true;
    controller.abort();
  };
}
