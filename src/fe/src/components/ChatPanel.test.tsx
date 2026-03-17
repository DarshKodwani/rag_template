import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ChatPanel } from "./ChatPanel";

// Mock the API client
vi.mock("../api/client", () => ({
  sendChat: vi.fn(),
  docUrl: vi.fn((path: string) => `http://localhost:8000${path}`),
}));

import { sendChat } from "../api/client";
const mockSendChat = vi.mocked(sendChat);

describe("ChatPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders empty state hint", () => {
    render(<ChatPanel />);
    expect(
      screen.getByText("Upload documents, then ask a question.")
    ).toBeInTheDocument();
  });

  it("renders chat heading", () => {
    render(<ChatPanel />);
    expect(screen.getByRole("heading", { name: "Chat" })).toBeInTheDocument();
  });

  it("has a textarea and send button", () => {
    render(<ChatPanel />);
    expect(
      screen.getByPlaceholderText(/Ask a question/i)
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /send/i })).toBeInTheDocument();
  });

  it("send button is disabled when input is empty", () => {
    render(<ChatPanel />);
    expect(screen.getByRole("button", { name: /send/i })).toBeDisabled();
  });

  it("send button enables when input has text", async () => {
    const user = userEvent.setup();
    render(<ChatPanel />);

    await user.type(screen.getByPlaceholderText(/Ask a question/i), "hello");
    expect(screen.getByRole("button", { name: /send/i })).toBeEnabled();
  });

  it("sends a message and displays the response", async () => {
    const user = userEvent.setup();
    mockSendChat.mockResolvedValueOnce({
      answer: "The answer is 42.",
      citations: [],
    });

    render(<ChatPanel />);

    await user.type(screen.getByPlaceholderText(/Ask a question/i), "What is the answer?");
    await user.click(screen.getByRole("button", { name: /send/i }));

    // User message appears
    expect(await screen.findByText("What is the answer?")).toBeInTheDocument();
    // Assistant response appears
    expect(await screen.findByText("The answer is 42.")).toBeInTheDocument();
    // Empty hint disappears
    expect(
      screen.queryByText("Upload documents, then ask a question.")
    ).not.toBeInTheDocument();
  });

  it("displays error message when API fails", async () => {
    const user = userEvent.setup();
    mockSendChat.mockRejectedValueOnce(new Error("Network error"));

    render(<ChatPanel />);

    await user.type(screen.getByPlaceholderText(/Ask a question/i), "test");
    await user.click(screen.getByRole("button", { name: /send/i }));

    expect(await screen.findByText(/Error: .*Network error/)).toBeInTheDocument();
  });

  it("sends on Enter key", async () => {
    const user = userEvent.setup();
    mockSendChat.mockResolvedValueOnce({
      answer: "Response",
      citations: [],
    });

    render(<ChatPanel />);
    const textarea = screen.getByPlaceholderText(/Ask a question/i);

    await user.type(textarea, "hello{Enter}");

    expect(await screen.findByText("Response")).toBeInTheDocument();
  });

  it("does not send on Shift+Enter", async () => {
    const user = userEvent.setup();
    render(<ChatPanel />);
    const textarea = screen.getByPlaceholderText(/Ask a question/i);

    await user.type(textarea, "hello{Shift>}{Enter}{/Shift}");

    expect(mockSendChat).not.toHaveBeenCalled();
  });

  it("displays citations with the response", async () => {
    const user = userEvent.setup();
    mockSendChat.mockResolvedValueOnce({
      answer: "See source.",
      citations: [
        {
          doc_name: "report.pdf",
          doc_path: "/documents/report.pdf",
          page: 3,
          section: "Intro",
          snippet: "Relevant text here.",
          chunk_id: "abc123",
        },
      ],
    });

    render(<ChatPanel />);
    await user.type(screen.getByPlaceholderText(/Ask a question/i), "question");
    await user.click(screen.getByRole("button", { name: /send/i }));

    expect(await screen.findByText("report.pdf")).toBeInTheDocument();
    expect(screen.getByText("Relevant text here.")).toBeInTheDocument();
  });

  it("does not send a second message while loading", async () => {
    const user = userEvent.setup();
    let resolveSend!: (v: { answer: string; citations: never[] }) => void;
    mockSendChat.mockImplementationOnce(
      () => new Promise((r) => { resolveSend = r; })
    );

    render(<ChatPanel />);
    const textarea = screen.getByPlaceholderText(/Ask a question/i);

    await user.type(textarea, "hello");
    await user.click(screen.getByRole("button", { name: /send/i }));

    // Now loading is true; textarea is disabled but fireEvent bypasses that
    fireEvent.keyDown(textarea, { key: "Enter" });

    expect(mockSendChat).toHaveBeenCalledTimes(1);

    // Resolve to clean up
    resolveSend({ answer: "done", citations: [] });
    expect(await screen.findByText("done")).toBeInTheDocument();
  });

  it("includes previous messages as history on second send", async () => {
    const user = userEvent.setup();
    mockSendChat
      .mockResolvedValueOnce({ answer: "First answer", citations: [] })
      .mockResolvedValueOnce({ answer: "Second answer", citations: [] });

    render(<ChatPanel />);
    const textarea = screen.getByPlaceholderText(/Ask a question/i);

    // First message
    await user.type(textarea, "msg1");
    await user.click(screen.getByRole("button", { name: /send/i }));
    expect(await screen.findByText("First answer")).toBeInTheDocument();

    // Second message — messages array is now non-empty so history map callback runs
    await user.type(textarea, "msg2");
    await user.click(screen.getByRole("button", { name: /send/i }));
    expect(await screen.findByText("Second answer")).toBeInTheDocument();

    expect(mockSendChat).toHaveBeenCalledTimes(2);
    // Second call should have history containing the first exchange
    const secondCallHistory = mockSendChat.mock.calls[1][1];
    expect(secondCallHistory).toEqual([
      { role: "user", content: "msg1" },
      { role: "assistant", content: "First answer" },
    ]);
  });
});
