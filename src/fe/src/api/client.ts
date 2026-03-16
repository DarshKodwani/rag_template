/** API client — all calls go through this module. */

import type { ChatMessage, ChatResponse, IngestResponse } from "../types";

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
