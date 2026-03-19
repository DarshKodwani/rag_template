import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { ChatPanel } from "@/components/ChatPanel";

// Mock the API client
vi.mock("@/api/client", () => ({
  sendChat: vi.fn(),
  submitFeedback: vi.fn(),
  docUrl: vi.fn((path: string) => `http://localhost:8000${path}`),
}));

import { sendChat, submitFeedback } from "@/api/client";
const mockSendChat = vi.mocked(sendChat);
const mockSubmitFeedback = vi.mocked(submitFeedback);

function renderChat() {
  return render(
    <MemoryRouter>
      <ChatPanel />
    </MemoryRouter>,
  );
}

describe("ChatPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders empty state hint", () => {
    renderChat();
    expect(
      screen.getByText("Ask a question about your indexed documents.")
    ).toBeInTheDocument();
  });

  it("renders suggested prompts in empty state", () => {
    renderChat();
    const buttons = screen.getAllByRole("button").filter(b => b.classList.contains("suggested-prompt"));
    expect(buttons.length).toBe(4);
    expect(buttons[0]).toHaveTextContent("AnaCredit");
  });

  it("clicking a suggested prompt fills the input", async () => {
    const user = userEvent.setup();
    renderChat();
    const buttons = screen.getAllByRole("button").filter(b => b.classList.contains("suggested-prompt"));
    await user.click(buttons[0]);
    const textarea = screen.getByPlaceholderText(/Ask a question/i) as HTMLTextAreaElement;
    expect(textarea.value).toBe("What is AnaCredit and what is its purpose?");
  });

  it("renders chat heading", () => {
    renderChat();
    expect(screen.getByRole("heading", { name: "Chat" })).toBeInTheDocument();
  });

  it("has a textarea and send button", () => {
    renderChat();
    expect(
      screen.getByPlaceholderText(/Ask a question/i)
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /send/i })).toBeInTheDocument();
  });

  it("send button is disabled when input is empty", () => {
    renderChat();
    expect(screen.getByRole("button", { name: /send/i })).toBeDisabled();
  });

  it("send button enables when input has text", async () => {
    const user = userEvent.setup();
    renderChat();

    await user.type(screen.getByPlaceholderText(/Ask a question/i), "hello");
    expect(screen.getByRole("button", { name: /send/i })).toBeEnabled();
  });

  it("sends a message and displays the response", async () => {
    const user = userEvent.setup();
    mockSendChat.mockResolvedValueOnce({
      answer: "The answer is 42.",
      citations: [],
    });

    renderChat();

    await user.type(screen.getByPlaceholderText(/Ask a question/i), "What is the answer?");
    await user.click(screen.getByRole("button", { name: /send/i }));

    // User message appears
    expect(await screen.findByText("What is the answer?")).toBeInTheDocument();
    // Assistant response appears
    expect(await screen.findByText("The answer is 42.")).toBeInTheDocument();
    // Empty hint disappears
    expect(
      screen.queryByText("Ask a question about your indexed documents.")
    ).not.toBeInTheDocument();
  });

  it("displays error message when API fails", async () => {
    const user = userEvent.setup();
    mockSendChat.mockRejectedValueOnce(new Error("Network error"));

    renderChat();

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

    renderChat();
    const textarea = screen.getByPlaceholderText(/Ask a question/i);

    await user.type(textarea, "hello{Enter}");

    expect(await screen.findByText("Response")).toBeInTheDocument();
  });

  it("does not send on Shift+Enter", async () => {
    const user = userEvent.setup();
    renderChat();
    const textarea = screen.getByPlaceholderText(/Ask a question/i);

    await user.type(textarea, "hello{Shift>}{Enter}{/Shift}");

    expect(mockSendChat).not.toHaveBeenCalled();
  });

  it("displays citations with the response", async () => {
    const user = userEvent.setup();
    mockSendChat.mockResolvedValueOnce({
      answer: "See source [Source 1].",
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

    renderChat();
    await user.type(screen.getByPlaceholderText(/Ask a question/i), "question");
    await user.click(screen.getByRole("button", { name: /send/i }));

    // Citation chip visible
    expect(await screen.findByText("report.pdf")).toBeInTheDocument();
    // Inline badge + chip both rendered (badge in text, chip below)
    const titled = screen.getAllByTitle("report.pdf");
    expect(titled.length).toBe(2); // badge + chip
  });

  it("does not send a second message while loading", async () => {
    const user = userEvent.setup();
    let resolveSend!: (v: { answer: string; citations: never[] }) => void;
    mockSendChat.mockImplementationOnce(
      () => new Promise((r) => { resolveSend = r; })
    );

    renderChat();
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

    renderChat();
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

  it("clicking an inline badge opens the citation popover", async () => {
    const user = userEvent.setup();
    mockSendChat.mockResolvedValueOnce({
      answer: "Info [Source 1] here.",
      citations: [
        {
          doc_name: "a.pdf",
          doc_path: "/documents/a.pdf",
          page: 1,
          snippet: "Snippet A",
          chunk_id: "c1",
        },
      ],
    });

    renderChat();
    await user.type(screen.getByPlaceholderText(/Ask a question/i), "q");
    await user.click(screen.getByRole("button", { name: /send/i }));

    // Wait for message to render
    await screen.findByText("a.pdf");

    // Click the inline badge (first element with that title is the badge)
    const badges = screen.getAllByTitle("a.pdf");
    await user.click(badges[0]); // badge

    // Popover should appear with snippet
    expect(screen.getByText("Snippet A")).toBeInTheDocument();
    expect(screen.getByText("Page 1")).toBeInTheDocument();
  });

  it("clicking a citation chip opens the popover", async () => {
    const user = userEvent.setup();
    mockSendChat.mockResolvedValueOnce({
      answer: "Info [Source 1].",
      citations: [
        {
          doc_name: "b.pdf",
          doc_path: "/documents/b.pdf",
          section: "Methods",
          snippet: "Snippet B",
          chunk_id: "c2",
        },
      ],
    });

    renderChat();
    await user.type(screen.getByPlaceholderText(/Ask a question/i), "q");
    await user.click(screen.getByRole("button", { name: /send/i }));

    await screen.findByText("b.pdf");

    // Click the chip (second element with title)
    const chips = screen.getAllByTitle("b.pdf");
    await user.click(chips[1]); // chip

    expect(screen.getByText("§ Methods")).toBeInTheDocument();
    expect(screen.getByText("Snippet B")).toBeInTheDocument();
  });

  it("keeps raw text for out-of-range source references", async () => {
    const user = userEvent.setup();
    mockSendChat.mockResolvedValueOnce({
      answer: "See [Source 99] for details.",
      citations: [
        {
          doc_name: "c.pdf",
          doc_path: "/documents/c.pdf",
          snippet: "text",
          chunk_id: "c1",
        },
      ],
    });

    renderChat();
    await user.type(screen.getByPlaceholderText(/Ask a question/i), "q");
    await user.click(screen.getByRole("button", { name: /send/i }));

    // Out-of-range reference kept as plain text
    expect(await screen.findByText(/\[Source 99\]/)).toBeInTheDocument();
  });

  it("shows reasoning toggle when response has ## Reasoning section", async () => {
    const user = userEvent.setup();
    mockSendChat.mockResolvedValueOnce({
      answer: "## Answer\nRemove the instrument.\n\n## Reasoning\n1. [Source 1] states the threshold is €25,000.\n2. [Source 2] says instruments below threshold stop reporting.",
      citations: [
        { doc_name: "a.pdf", doc_path: "/documents/a.pdf", snippet: "threshold", chunk_id: "c1" },
        { doc_name: "b.pdf", doc_path: "/documents/b.pdf", snippet: "stop reporting", chunk_id: "c2" },
      ],
    });

    renderChat();
    await user.type(screen.getByPlaceholderText(/Ask a question/i), "q");
    await user.click(screen.getByRole("button", { name: /send/i }));

    // Answer rendered
    expect(await screen.findByText(/Remove the instrument/)).toBeInTheDocument();
    // Reasoning toggle present
    const toggle = screen.getByText(/Show reasoning steps/);
    expect(toggle).toBeInTheDocument();
  });

  it("expands and collapses reasoning steps", async () => {
    const user = userEvent.setup();
    mockSendChat.mockResolvedValueOnce({
      answer: "## Answer\nDo X.\n\n## Reasoning\n1. Step one.\n2. Step two.",
      citations: [],
    });

    renderChat();
    await user.type(screen.getByPlaceholderText(/Ask a question/i), "q");
    await user.click(screen.getByRole("button", { name: /send/i }));

    await screen.findByText(/Do X/);

    // Steps hidden initially
    expect(screen.queryByText(/Step one/)).not.toBeInTheDocument();

    // Expand
    await user.click(screen.getByText(/Show reasoning steps/));
    expect(screen.getByText(/Step one/)).toBeInTheDocument();
    expect(screen.getByText(/Step two/)).toBeInTheDocument();

    // Collapse
    await user.click(screen.getByText(/Hide reasoning steps/));
    expect(screen.queryByText(/Step one/)).not.toBeInTheDocument();
  });

  it("shows 'Ask about this step' buttons that prefill input", async () => {
    const user = userEvent.setup();
    mockSendChat.mockResolvedValueOnce({
      answer: "## Answer\nDo X.\n\n## Reasoning\n1. First step.\n2. Second step.",
      citations: [],
    });

    renderChat();
    await user.type(screen.getByPlaceholderText(/Ask a question/i), "q");
    await user.click(screen.getByRole("button", { name: /send/i }));

    await screen.findByText(/Do X/);
    await user.click(screen.getByText(/Show reasoning steps/));

    const askBtns = screen.getAllByText("Ask about this step");
    expect(askBtns.length).toBe(2);

    await user.click(askBtns[1]); // second step
    const textarea = screen.getByPlaceholderText(/Ask a question/i) as HTMLTextAreaElement;
    expect(textarea.value).toBe("Regarding reasoning step 2: ");
  });

  it("does not show reasoning section for plain responses", async () => {
    const user = userEvent.setup();
    mockSendChat.mockResolvedValueOnce({
      answer: "AnaCredit is a dataset [Source 1].",
      citations: [
        { doc_name: "a.pdf", doc_path: "/documents/a.pdf", snippet: "s", chunk_id: "c1" },
      ],
    });

    renderChat();
    await user.type(screen.getByPlaceholderText(/Ask a question/i), "q");
    await user.click(screen.getByRole("button", { name: /send/i }));

    await screen.findByText(/AnaCredit is a dataset/);
    expect(screen.queryByText(/Show reasoning steps/)).not.toBeInTheDocument();
  });

  it("shows '📖 Factual answer' badge for plain responses", async () => {
    const user = userEvent.setup();
    mockSendChat.mockResolvedValueOnce({
      answer: "AnaCredit is a dataset.",
      citations: [],
    });

    renderChat();
    await user.type(screen.getByPlaceholderText(/Ask a question/i), "q");
    await user.click(screen.getByRole("button", { name: /send/i }));

    await screen.findByText(/AnaCredit is a dataset/);
    const badge = screen.getByText(/Factual answer/);
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveClass("badge-factual");
  });

  it("shows '🔍 Reasoned answer' badge for reasoning responses", async () => {
    const user = userEvent.setup();
    mockSendChat.mockResolvedValueOnce({
      answer: "## Answer\nDo X.\n\n## Reasoning\n1. Step one.",
      citations: [],
    });

    renderChat();
    await user.type(screen.getByPlaceholderText(/Ask a question/i), "q");
    await user.click(screen.getByRole("button", { name: /send/i }));

    await screen.findByText(/Do X/);
    const badge = screen.getByText(/Reasoned answer/);
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveClass("badge-reasoned");
  });

  it("shows feedback buttons on assistant messages", async () => {
    const user = userEvent.setup();
    mockSendChat.mockResolvedValueOnce({ answer: "Hello!", citations: [] });

    renderChat();
    await user.type(screen.getByPlaceholderText(/Ask a question/i), "q");
    await user.click(screen.getByRole("button", { name: /send/i }));

    await screen.findByText("Hello!");
    expect(screen.getByText("Was this helpful?")).toBeInTheDocument();
    expect(screen.getByTitle("Thumbs up")).toBeInTheDocument();
    expect(screen.getByTitle("Thumbs down")).toBeInTheDocument();
    expect(screen.getByText("Suggest better answer")).toBeInTheDocument();
  });

  it("submits thumbs up feedback and shows thank you", async () => {
    const user = userEvent.setup();
    mockSendChat.mockResolvedValueOnce({ answer: "Hello!", citations: [] });
    mockSubmitFeedback.mockResolvedValueOnce({ id: 1, status: "saved" });

    renderChat();
    await user.type(screen.getByPlaceholderText(/Ask a question/i), "q");
    await user.click(screen.getByRole("button", { name: /send/i }));

    await screen.findByText("Hello!");
    await user.click(screen.getByTitle("Thumbs up"));

    expect(await screen.findByText(/Thanks for your feedback/)).toBeInTheDocument();
    expect(mockSubmitFeedback).toHaveBeenCalledWith(
      expect.objectContaining({ query: "q", answer: "Hello!", rating: "up" }),
    );
  });

  it("submits thumbs down feedback and shows thank you", async () => {
    const user = userEvent.setup();
    mockSendChat.mockResolvedValueOnce({ answer: "Wrong!", citations: [] });
    mockSubmitFeedback.mockResolvedValueOnce({ id: 1, status: "saved" });

    renderChat();
    await user.type(screen.getByPlaceholderText(/Ask a question/i), "q");
    await user.click(screen.getByRole("button", { name: /send/i }));

    await screen.findByText("Wrong!");
    await user.click(screen.getByTitle("Thumbs down"));

    expect(await screen.findByText(/Thanks for your feedback/)).toBeInTheDocument();
    expect(mockSubmitFeedback).toHaveBeenCalledWith(
      expect.objectContaining({ rating: "down" }),
    );
  });

  it("opens suggestion form and submits suggested answer", async () => {
    const user = userEvent.setup();
    mockSendChat.mockResolvedValueOnce({ answer: "Bad answer.", citations: [] });
    mockSubmitFeedback.mockResolvedValueOnce({ id: 2, status: "saved" });

    renderChat();
    await user.type(screen.getByPlaceholderText(/Ask a question/i), "q");
    await user.click(screen.getByRole("button", { name: /send/i }));

    await screen.findByText("Bad answer.");

    // Open suggestion form
    await user.click(screen.getByText("Suggest better answer"));
    const suggestionInput = screen.getByPlaceholderText("What would be a better answer?");
    expect(suggestionInput).toBeInTheDocument();

    // Type suggestion and submit
    await user.type(suggestionInput, "The correct answer is X.");
    await user.click(screen.getByText("Submit suggestion"));

    expect(await screen.findByText(/Thanks for your feedback/)).toBeInTheDocument();
    expect(mockSubmitFeedback).toHaveBeenCalledWith(
      expect.objectContaining({
        rating: "down",
        suggested_answer: "The correct answer is X.",
      }),
    );
  });

  it("can cancel the suggestion form", async () => {
    const user = userEvent.setup();
    mockSendChat.mockResolvedValueOnce({ answer: "Answer.", citations: [] });

    renderChat();
    await user.type(screen.getByPlaceholderText(/Ask a question/i), "q");
    await user.click(screen.getByRole("button", { name: /send/i }));

    await screen.findByText("Answer.");

    // Open then cancel
    await user.click(screen.getByText("Suggest better answer"));
    expect(screen.getByPlaceholderText("What would be a better answer?")).toBeInTheDocument();

    await user.click(screen.getByText("Cancel"));
    expect(screen.queryByPlaceholderText("What would be a better answer?")).not.toBeInTheDocument();
  });

  it("does not show feedback buttons on user messages", async () => {
    const user = userEvent.setup();
    mockSendChat.mockResolvedValueOnce({ answer: "Hi!", citations: [] });

    renderChat();
    await user.type(screen.getByPlaceholderText(/Ask a question/i), "hello");
    await user.click(screen.getByRole("button", { name: /send/i }));

    await screen.findByText("Hi!");
    // Only one feedback bar (on the assistant message, not the user message)
    const feedbackLabels = screen.getAllByText("Was this helpful?");
    expect(feedbackLabels.length).toBe(1);
  });

  it("keeps feedback buttons working when submitFeedback fails silently", async () => {
    const user = userEvent.setup();
    mockSendChat.mockResolvedValueOnce({ answer: "Hello!", citations: [] });
    mockSubmitFeedback.mockRejectedValueOnce(new Error("Network error"));

    renderChat();
    await user.type(screen.getByPlaceholderText(/Ask a question/i), "q");
    await user.click(screen.getByRole("button", { name: /send/i }));

    await screen.findByText("Hello!");
    await user.click(screen.getByTitle("Thumbs up"));

    // Should still show the feedback buttons (not thank you) since it failed
    await new Promise((r) => setTimeout(r, 50));
    expect(screen.getByText("Was this helpful?")).toBeInTheDocument();
  });
});
