/** Shared TypeScript types that mirror the backend Pydantic models. */

export interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

export interface Citation {
  doc_name: string;
  doc_path: string;
  page?: number;
  section?: string;
  snippet: string;
  chunk_id: string;
}

export interface ChatResponse {
  answer: string;
  citations: Citation[];
}

export interface IngestResponse {
  status: string;
  indexed: number;
  errors: string[];
}

/** A message as shown in the chat UI (may include citations). */
export interface UIMessage extends ChatMessage {
  citations?: Citation[];
}
