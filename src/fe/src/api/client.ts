/** API client — all calls go through this module. */

import type { ChatMessage, ChatResponse, DocumentInfo, FeedbackRequest, FeedbackResponse, IngestResponse } from "../types";

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export async function sendChat(
  message: string,
  chatHistory: ChatMessage[]
): Promise<ChatResponse> {
  return post<ChatResponse>("/chat", { message, chat_history: chatHistory });
}

export async function reindexAll(): Promise<IngestResponse> {
  return post<IngestResponse>("/ingest/reindex", {});
}

export async function uploadFile(file: File): Promise<IngestResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${BASE_URL}/ingest/upload`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json() as Promise<IngestResponse>;
}

export function docUrl(docPath: string): string {
  // Strip leading path segments up to "documents/" if present
  const normalized = docPath.startsWith("/") ? docPath : `/${docPath}`;
  return `${BASE_URL}${normalized}`;
}

export async function listDocuments(): Promise<DocumentInfo[]> {
  const res = await fetch(`${BASE_URL}/ingest/documents`);
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json() as Promise<DocumentInfo[]>;
}

export function reindexStream(
  onEvent: (event: Record<string, unknown>) => void,
  onDone: () => void,
  onError: (err: string) => void,
): () => void {
  const ctrl = new AbortController();

  fetch(`${BASE_URL}/ingest/reindex/stream`, {
    method: "POST",
    signal: ctrl.signal,
  })
    .then(async (res) => {
      if (!res.ok || !res.body) {
        onError(`HTTP ${res.status}`);
        return;
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              onEvent(JSON.parse(line.slice(6)));
            } catch { /* skip malformed */ }
          }
        }
      }
      onDone();
    })
    .catch((err) => {
      if (!ctrl.signal.aborted) onError(String(err));
    });

  return () => ctrl.abort();
}

export async function submitFeedback(feedback: FeedbackRequest): Promise<FeedbackResponse> {
  return post<FeedbackResponse>("/feedback", feedback);
}
