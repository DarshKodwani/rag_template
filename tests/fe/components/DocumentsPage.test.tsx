import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { DocumentsPage } from "@/components/DocumentsPage";

vi.mock("@/api/client", () => ({
  uploadFile: vi.fn(),
  reindexStream: vi.fn(),
  listDocuments: vi.fn(),
}));

import { uploadFile, reindexStream, listDocuments } from "@/api/client";
const mockUploadFile = vi.mocked(uploadFile);
const mockReindexStream = vi.mocked(reindexStream);
const mockListDocuments = vi.mocked(listDocuments);

function renderPage() {
  return render(
    <MemoryRouter>
      <DocumentsPage />
    </MemoryRouter>,
  );
}

describe("DocumentsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockListDocuments.mockResolvedValue([]);
  });

  it("renders heading", () => {
    renderPage();
    expect(
      screen.getByRole("heading", { name: "Manage Documents" }),
    ).toBeInTheDocument();
  });

  it("renders back link", () => {
    renderPage();
    expect(screen.getByText("← Home")).toBeInTheDocument();
  });

  it("renders upload section", () => {
    renderPage();
    expect(screen.getByText("Upload a document")).toBeInTheDocument();
    expect(screen.getByText("Upload & Index")).toBeInTheDocument();
  });

  it("renders reindex section", () => {
    renderPage();
    expect(screen.getByText("Re-index all documents")).toBeInTheDocument();
    expect(screen.getByText("🔄 Reindex All")).toBeInTheDocument();
  });

  it("shows indexed document count in toggle button", async () => {
    mockListDocuments.mockResolvedValueOnce([
      {
        doc_name: "report.pdf",
        doc_id: "abc",
        chunks: 10,
        indexed_at: "2026-03-19T12:00:00Z",
      },
    ]);
    renderPage();
    await waitFor(() =>
      expect(
        screen.getByText(/View indexed documents \(1\)/),
      ).toBeInTheDocument(),
    );
  });

  it("toggles document list visibility", async () => {
    const user = userEvent.setup();
    mockListDocuments.mockResolvedValueOnce([
      {
        doc_name: "a.pdf",
        doc_id: "x",
        chunks: 5,
        indexed_at: "2026-03-19T12:00:00Z",
      },
    ]);
    renderPage();

    await waitFor(() =>
      expect(screen.getByText(/View indexed documents/)).toBeInTheDocument(),
    );

    // Open the list
    await user.click(screen.getByText(/View indexed documents/));
    expect(screen.getByText("a.pdf")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();

    // Close the list
    await user.click(screen.getByText(/Hide indexed documents/));
    expect(screen.queryByText("a.pdf")).not.toBeInTheDocument();
  });

  it("shows empty message when no documents indexed", async () => {
    const user = userEvent.setup();
    renderPage();
    await waitFor(() =>
      expect(screen.getByText(/View indexed documents/)).toBeInTheDocument(),
    );
    await user.click(screen.getByText(/View indexed documents/));
    expect(screen.getByText("No documents indexed yet.")).toBeInTheDocument();
  });

  it("uploads a file and shows success", async () => {
    const user = userEvent.setup();
    mockUploadFile.mockResolvedValueOnce({
      status: "ok",
      indexed: 8,
      errors: [],
    });
    renderPage();

    const file = new File(["data"], "test.txt", { type: "text/plain" });
    const input = document.querySelector(
      'input[type="file"]',
    ) as HTMLInputElement;
    await user.upload(input, file);
    await user.click(screen.getByText("Upload & Index"));

    expect(
      await screen.findByText(/Indexed 8 chunk\(s\) from "test.txt"/),
    ).toBeInTheDocument();
  });

  it("shows error on upload failure", async () => {
    const user = userEvent.setup();
    mockUploadFile.mockRejectedValueOnce(new Error("fail"));
    renderPage();

    const file = new File(["data"], "test.txt", { type: "text/plain" });
    const input = document.querySelector(
      'input[type="file"]',
    ) as HTMLInputElement;
    await user.upload(input, file);
    await user.click(screen.getByText("Upload & Index"));

    expect(await screen.findByText(/Upload failed.*fail/)).toBeInTheDocument();
  });

  it("shows partial status on upload", async () => {
    const user = userEvent.setup();
    mockUploadFile.mockResolvedValueOnce({
      status: "partial",
      indexed: 2,
      errors: ["some error"],
    });
    renderPage();

    const file = new File(["data"], "test.txt", { type: "text/plain" });
    const input = document.querySelector(
      'input[type="file"]',
    ) as HTMLInputElement;
    await user.upload(input, file);
    await user.click(screen.getByText("Upload & Index"));

    expect(await screen.findByText(/Partial.*some error/)).toBeInTheDocument();
  });

  it("does nothing when no file selected", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(screen.getByText("Upload & Index"));
    expect(mockUploadFile).not.toHaveBeenCalled();
  });

  it("starts reindex with SSE and shows progress", async () => {
    const user = userEvent.setup();
    mockReindexStream.mockImplementation((onEvent: (e: Record<string, unknown>) => void, onDone: () => void) => {
      onEvent({ type: "start", total: 2 });
      onEvent({
        type: "progress",
        current: 1,
        total: 2,
        doc_name: "a.pdf",
      });
      onEvent({ type: "done", indexed: 10, errors: [] });
      onDone();
      return () => {};
    });

    renderPage();
    await user.click(screen.getByText("🔄 Reindex All"));

    expect(
      await screen.findByText(/Reindexed 10 chunk\(s\)/),
    ).toBeInTheDocument();
  });

  it("handles reindex SSE error event", async () => {
    const user = userEvent.setup();
    mockReindexStream.mockImplementation((onEvent: (e: Record<string, unknown>) => void, onDone: () => void) => {
      onEvent({ type: "error", message: "API keys missing." });
      onDone();
      return () => {};
    });

    renderPage();
    await user.click(screen.getByText("🔄 Reindex All"));

    expect(
      await screen.findByText(/API keys missing/),
    ).toBeInTheDocument();
  });

  it("handles reindex stream failure", async () => {
    const user = userEvent.setup();
    mockReindexStream.mockImplementation((_onEvent: unknown, _onDone: unknown, onError: (err: string) => void) => {
      onError("Connection lost");
      return () => {};
    });

    renderPage();
    await user.click(screen.getByText("🔄 Reindex All"));

    expect(
      await screen.findByText(/Reindex failed.*Connection lost/),
    ).toBeInTheDocument();
  });

  it("shows done errors in status", async () => {
    const user = userEvent.setup();
    mockReindexStream.mockImplementation((onEvent: (e: Record<string, unknown>) => void, onDone: () => void) => {
      onEvent({ type: "done", indexed: 5, errors: ["bad file"] });
      onDone();
      return () => {};
    });

    renderPage();
    await user.click(screen.getByText("🔄 Reindex All"));

    expect(
      await screen.findByText(/Reindexed 5 chunk.*bad file/),
    ).toBeInTheDocument();
  });
});
