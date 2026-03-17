import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { UploadPanel } from "@/components/UploadPanel";

vi.mock("@/api/client", () => ({
  uploadFile: vi.fn(),
  reindexAll: vi.fn(),
}));

import { uploadFile, reindexAll } from "@/api/client";
const mockUploadFile = vi.mocked(uploadFile);
const mockReindexAll = vi.mocked(reindexAll);

describe("UploadPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders Documents heading", () => {
    render(<UploadPanel />);
    expect(
      screen.getByRole("heading", { name: "Documents" })
    ).toBeInTheDocument();
  });

  it("renders file input and buttons", () => {
    render(<UploadPanel />);
    expect(screen.getByText("Upload & Index")).toBeInTheDocument();
    expect(screen.getByText("🔄 Reindex All")).toBeInTheDocument();
  });

  it("uploads a file and shows success status", async () => {
    const user = userEvent.setup();
    mockUploadFile.mockResolvedValueOnce({
      status: "ok",
      indexed: 5,
      errors: [],
    });

    render(<UploadPanel />);

    const file = new File(["hello"], "test.txt", { type: "text/plain" });
    const input = screen.getByAcceptingUpload();

    await user.upload(input, file);
    await user.click(screen.getByText("Upload & Index"));

    expect(
      await screen.findByText(/Indexed 5 chunk\(s\) from "test.txt"/)
    ).toBeInTheDocument();
  });

  it("shows partial status on upload errors", async () => {
    const user = userEvent.setup();
    mockUploadFile.mockResolvedValueOnce({
      status: "partial",
      indexed: 2,
      errors: ["some error"],
    });

    render(<UploadPanel />);

    const file = new File(["data"], "doc.pdf", { type: "application/pdf" });
    const input = screen.getByAcceptingUpload();

    await user.upload(input, file);
    await user.click(screen.getByText("Upload & Index"));

    expect(await screen.findByText(/Partial.*some error/)).toBeInTheDocument();
  });

  it("shows error when upload fails", async () => {
    const user = userEvent.setup();
    mockUploadFile.mockRejectedValueOnce(new Error("Network error"));

    render(<UploadPanel />);

    const file = new File(["data"], "test.txt", { type: "text/plain" });
    const input = screen.getByAcceptingUpload();

    await user.upload(input, file);
    await user.click(screen.getByText("Upload & Index"));

    expect(
      await screen.findByText(/Upload failed.*Network error/)
    ).toBeInTheDocument();
  });

  it("reindexes and shows success status", async () => {
    const user = userEvent.setup();
    mockReindexAll.mockResolvedValueOnce({
      status: "ok",
      indexed: 100,
      errors: [],
    });

    render(<UploadPanel />);
    await user.click(screen.getByText("🔄 Reindex All"));

    expect(
      await screen.findByText(/Reindexed 100 chunk\(s\)/)
    ).toBeInTheDocument();
  });

  it("shows error when reindex fails", async () => {
    const user = userEvent.setup();
    mockReindexAll.mockRejectedValueOnce(new Error("Server down"));

    render(<UploadPanel />);
    await user.click(screen.getByText("🔄 Reindex All"));

    expect(
      await screen.findByText(/Reindex failed.*Server down/)
    ).toBeInTheDocument();
  });

  it("shows partial status on reindex errors", async () => {
    const user = userEvent.setup();
    mockReindexAll.mockResolvedValueOnce({
      status: "partial",
      indexed: 50,
      errors: ["file corrupt"],
    });

    render(<UploadPanel />);
    await user.click(screen.getByText("🔄 Reindex All"));

    expect(
      await screen.findByText(/Partial.*file corrupt/)
    ).toBeInTheDocument();
  });

  it("does nothing when no file is selected", async () => {
    const user = userEvent.setup();
    render(<UploadPanel />);

    await user.click(screen.getByText("Upload & Index"));

    expect(mockUploadFile).not.toHaveBeenCalled();
  });

  it("handles unmount during upload (fileRef becomes null)", async () => {
    const user = userEvent.setup();
    let resolveUpload!: (v: { status: string; indexed: number; errors: string[] }) => void;
    mockUploadFile.mockImplementationOnce(
      () => new Promise((r) => { resolveUpload = r; })
    );

    const { unmount } = render(<UploadPanel />);

    const file = new File(["data"], "test.txt", { type: "text/plain" });
    const input = screen.getByAcceptingUpload();
    await user.upload(input, file);
    await user.click(screen.getByText("Upload & Index"));

    // Unmount while upload is pending — fileRef.current becomes null
    unmount();

    // Resolve after unmount — the finally block runs with fileRef.current === null
    resolveUpload({ status: "ok", indexed: 1, errors: [] });
  });
});

// Helper to find file input
function getByAcceptingUpload() {
  return document.querySelector('input[type="file"]') as HTMLInputElement;
}

// Extend screen with helper
Object.defineProperty(screen, "getByAcceptingUpload", {
  value: getByAcceptingUpload,
});

declare module "@testing-library/react" {
  interface Screen {
    getByAcceptingUpload(): HTMLInputElement;
  }
}
