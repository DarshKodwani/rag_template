import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { sendChat, reindexAll, uploadFile, docUrl } from "./client";

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
});
