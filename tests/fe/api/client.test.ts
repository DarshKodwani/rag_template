import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  sendChat,
  reindexAll,
  uploadFile,
  docUrl,
  listDocuments,
  reindexStream,
  submitFeedback,
} from "@/api/client";

// Mock fetch globally
const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

describe("API client", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("sendChat", () => {
    it("sends a POST to /chat with message and history", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ answer: "Hello", citations: [] }),
      });

      const result = await sendChat("hi", [
        { role: "user" as const, content: "previous" },
      ]);

      expect(mockFetch).toHaveBeenCalledWith(
        "http://localhost:8000/chat",
        expect.objectContaining({
          method: "POST",
          headers: { "Content-Type": "application/json" },
        })
      );

      const body = JSON.parse(
        (mockFetch.mock.calls[0][1] as RequestInit).body as string
      );
      expect(body.message).toBe("hi");
      expect(body.chat_history).toEqual([{ role: "user", content: "previous" }]);
      expect(result.answer).toBe("Hello");
    });

    it("throws on non-ok response", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        text: () => Promise.resolve("Internal Server Error"),
        statusText: "Internal Server Error",
      });

      await expect(sendChat("fail", [])).rejects.toThrow("500");
    });

    it("falls back to statusText when text() throws", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 502,
        text: () => Promise.reject(new Error("cant read")),
        statusText: "Bad Gateway",
      });

      await expect(sendChat("fail", [])).rejects.toThrow("502: Bad Gateway");
    });
  });

  describe("reindexAll", () => {
    it("sends a POST to /ingest/reindex", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({ status: "ok", indexed: 10, errors: [] }),
      });

      const result = await reindexAll();

      expect(mockFetch).toHaveBeenCalledWith(
        "http://localhost:8000/ingest/reindex",
        expect.objectContaining({ method: "POST" })
      );
      expect(result.indexed).toBe(10);
    });
  });

  describe("uploadFile", () => {
    it("sends a POST to /ingest/upload with FormData", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({ status: "ok", indexed: 5, errors: [] }),
      });

      const file = new File(["content"], "test.txt", { type: "text/plain" });
      const result = await uploadFile(file);

      expect(mockFetch).toHaveBeenCalledWith(
        "http://localhost:8000/ingest/upload",
        expect.objectContaining({ method: "POST" })
      );
      const body = (mockFetch.mock.calls[0][1] as RequestInit).body;
      expect(body).toBeInstanceOf(FormData);
      expect(result.indexed).toBe(5);
    });

    it("throws on non-ok response", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 415,
        text: () => Promise.resolve("Unsupported Media Type"),
        statusText: "Unsupported Media Type",
      });

      const file = new File(["content"], "image.png", { type: "image/png" });
      await expect(uploadFile(file)).rejects.toThrow("415");
    });

    it("falls back to statusText when text() throws", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        text: () => Promise.reject(new Error("err")),
        statusText: "Server Error",
      });

      const file = new File(["x"], "a.txt", { type: "text/plain" });
      await expect(uploadFile(file)).rejects.toThrow("500: Server Error");
    });
  });

  describe("docUrl", () => {
    it("builds URL from path without leading slash", () => {
      expect(docUrl("documents/report.pdf")).toBe(
        "http://localhost:8000/documents/report.pdf"
      );
    });

    it("builds URL from path with leading slash", () => {
      expect(docUrl("/documents/report.pdf")).toBe(
        "http://localhost:8000/documents/report.pdf"
      );
    });
  });

  describe("listDocuments", () => {
    it("fetches GET /ingest/documents", async () => {
      const docs = [
        { doc_name: "a.pdf", doc_id: "x", chunks: 5, indexed_at: "2026-01-01" },
      ];
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(docs),
      });

      const result = await listDocuments();
      expect(mockFetch).toHaveBeenCalledWith(
        "http://localhost:8000/ingest/documents",
      );
      expect(result).toEqual(docs);
    });

    it("throws on non-ok response", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        text: () => Promise.resolve("error"),
        statusText: "Server Error",
      });

      await expect(listDocuments()).rejects.toThrow("500");
    });

    it("falls back to statusText when text() throws", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 503,
        text: () => Promise.reject(new Error("read fail")),
        statusText: "Service Unavailable",
      });

      await expect(listDocuments()).rejects.toThrow(
        "503: Service Unavailable",
      );
    });
  });

  describe("reindexStream", () => {
    it("calls POST /ingest/reindex/stream and processes SSE", async () => {
      const events: Record<string, unknown>[] = [];
      let doneCalled = false;

      // Create a fake ReadableStream with SSE data
      const sseData =
        'data: {"type":"start","total":1}\n\ndata: {"type":"done","indexed":5}\n\n';
      const encoder = new TextEncoder();
      const stream = new ReadableStream({
        start(controller) {
          controller.enqueue(encoder.encode(sseData));
          controller.close();
        },
      });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        body: stream,
      });

      const cancel = reindexStream(
        (evt) => events.push(evt),
        () => {
          doneCalled = true;
        },
        () => {},
      );

      // Wait for stream processing
      await new Promise((r) => setTimeout(r, 50));

      expect(events.length).toBe(2);
      expect(events[0]).toEqual({ type: "start", total: 1 });
      expect(events[1]).toEqual({ type: "done", indexed: 5 });
      expect(doneCalled).toBe(true);
      expect(typeof cancel).toBe("function");
    });

    it("calls onError on HTTP error", async () => {
      let errorMsg = "";
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        body: null,
      });

      reindexStream(
        () => {},
        () => {},
        (err) => {
          errorMsg = err;
        },
      );

      await new Promise((r) => setTimeout(r, 50));
      expect(errorMsg).toBe("HTTP 500");
    });

    it("calls onError on fetch rejection", async () => {
      let errorMsg = "";
      mockFetch.mockRejectedValueOnce(new Error("Network down"));

      reindexStream(
        () => {},
        () => {},
        (err) => {
          errorMsg = err;
        },
      );

      await new Promise((r) => setTimeout(r, 50));
      expect(errorMsg).toContain("Network down");
    });
  });

  describe("submitFeedback", () => {
    it("sends a POST to /feedback with feedback data", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ id: 1, status: "saved" }),
      });

      const result = await submitFeedback({
        query: "What is X?",
        answer: "X is Y.",
        rating: "up",
      });

      expect(mockFetch).toHaveBeenCalledWith(
        "http://localhost:8000/feedback",
        expect.objectContaining({
          method: "POST",
          headers: { "Content-Type": "application/json" },
        }),
      );

      const body = JSON.parse(
        (mockFetch.mock.calls[0][1] as RequestInit).body as string,
      );
      expect(body.query).toBe("What is X?");
      expect(body.rating).toBe("up");
      expect(result.id).toBe(1);
      expect(result.status).toBe("saved");
    });

    it("sends suggested_answer when provided", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ id: 2, status: "saved" }),
      });

      await submitFeedback({
        query: "q",
        answer: "a",
        rating: "down",
        suggested_answer: "better answer",
      });

      const body = JSON.parse(
        (mockFetch.mock.calls[0][1] as RequestInit).body as string,
      );
      expect(body.suggested_answer).toBe("better answer");
      expect(body.rating).toBe("down");
    });

    it("throws on non-ok response", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 422,
        text: () => Promise.resolve("Validation Error"),
        statusText: "Unprocessable Entity",
      });

      await expect(
        submitFeedback({ query: "q", answer: "a", rating: "up" }),
      ).rejects.toThrow("422");
    });
  });
});
