import { useState, useRef, useEffect, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { sendChat, submitFeedback } from "../api/client";
import type { Citation, UIMessage } from "../types";
import { CitationList } from "./CitationList";

/**
 * Parse assistant text replacing [Source N] markers with clickable badges.
 */
function renderWithCitations(
  text: string,
  citations: Citation[],
  onBadgeClick: (idx: number) => void,
): ReactNode[] {
  const parts: ReactNode[] = [];
  const regex = /\[Source\s+(\d+)\]/gi;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    const num = parseInt(match[1], 10);
    const idx = num - 1;
    if (idx >= 0 && idx < citations.length) {
      parts.push(
        <button
          key={`src-${match.index}`}
          className="citation-badge"
          onClick={() => onBadgeClick(idx)}
          title={citations[idx].doc_name}
        >
          {num}
        </button>,
      );
    } else {
      parts.push(match[0]);
    }
    lastIndex = regex.lastIndex;
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts;
}

/** Split an assistant response into answer + optional reasoning steps. */
function parseReasoning(text: string): {
  answer: string;
  steps: string[];
} {
  const reasoningIdx = text.indexOf("## Reasoning");
  if (reasoningIdx === -1) {
    // Also try without ##
    const altIdx = text.indexOf("**Reasoning**");
    if (altIdx === -1) return { answer: text, steps: [] };
    const answerPart = text.slice(0, altIdx).replace(/^## Answer\s*/i, "").replace(/^\*\*Answer\*\*\s*/i, "").trim();
    const reasoningBlock = text.slice(altIdx + "**Reasoning**".length).trim();
    const steps = reasoningBlock.split(/\n\d+\.\s/).filter(Boolean).map(s => s.trim());
    return { answer: answerPart, steps };
  }

  const answerIdx = text.indexOf("## Answer");
  const answerStart = answerIdx !== -1 ? answerIdx + "## Answer".length : 0;
  const answerPart = text.slice(answerStart, reasoningIdx).trim();
  const reasoningBlock = text.slice(reasoningIdx + "## Reasoning".length).trim();
  const steps = reasoningBlock.split(/\n\d+\.\s/).filter(Boolean).map(s => s.trim());
  return { answer: answerPart, steps };
}

const SUGGESTED_PROMPTS = [
  "What is AnaCredit and what is its purpose?",
  "Which entities are required to report under AnaCredit?",
  "What types of instruments are covered by AnaCredit reporting?",
  "A debtor's commitment amount dropped below the €25,000 reporting threshold mid-quarter but the instrument is still being reported. What should I do?",
];

export function ChatPanel() {
  const [messages, setMessages] = useState<UIMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeCitation, setActiveCitation] = useState<{
    msgIdx: number;
    citIdx: number;
  } | null>(null);
  const [expandedReasoning, setExpandedReasoning] = useState<Set<number>>(
    new Set(),
  );
  const [feedbackGiven, setFeedbackGiven] = useState<Map<number, "up" | "down">>(new Map());
  const [suggestionOpen, setSuggestionOpen] = useState<number | null>(null);
  const [suggestionText, setSuggestionText] = useState("");
  const [feedbackSending, setFeedbackSending] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function toggleReasoning(idx: number) {
    setExpandedReasoning((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  }

  function prefillStep(stepNum: number) {
    setInput(`Regarding reasoning step ${stepNum}: `);
  }

  async function handleFeedback(idx: number, rating: "up" | "down") {
    const msg = messages[idx];
    if (!msg || msg.role !== "assistant" || feedbackSending) return;

    // Find the user message that triggered this assistant response
    const userMsg = idx > 0 ? messages[idx - 1] : null;
    const query = userMsg?.role === "user" ? userMsg.content : "";

    setFeedbackSending(true);
    try {
      await submitFeedback({
        query,
        answer: msg.content,
        rating,
        citations: msg.citations,
      });
      setFeedbackGiven((prev) => new Map(prev).set(idx, rating));
    } catch {
      // Silently fail — the rating buttons will remain un-highlighted
    } finally {
      setFeedbackSending(false);
    }
  }

  async function handleSuggestionSubmit(idx: number) {
    const msg = messages[idx];
    if (!msg || msg.role !== "assistant" || !suggestionText.trim() || feedbackSending) return;

    const userMsg = idx > 0 ? messages[idx - 1] : null;
    const query = userMsg?.role === "user" ? userMsg.content : "";

    setFeedbackSending(true);
    try {
      await submitFeedback({
        query,
        answer: msg.content,
        rating: "down",
        suggested_answer: suggestionText.trim(),
        citations: msg.citations,
      });
      setFeedbackGiven((prev) => new Map(prev).set(idx, "down"));
      setSuggestionOpen(null);
      setSuggestionText("");
    } catch {
      // Silently fail
    } finally {
      setFeedbackSending(false);
    }
  }

  async function handleSend() {
    const text = input.trim();
    if (!text || loading) return;

    const userMsg: UIMessage = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const history = messages.map(({ role, content }) => ({ role, content }));
      const res = await sendChat(text, history);
      const assistantMsg: UIMessage = {
        role: "assistant",
        content: res.answer,
        citations: res.citations,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: unknown) {
      const errorMsg: UIMessage = {
        role: "assistant",
        content: `❌ Error: ${String(err)}`,
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
    }
  }

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <Link to="/" className="back-link">← Home</Link>
        <h2>Chat</h2>
      </div>
      <div className="message-list">
        {messages.length === 0 && (
          <div className="empty-state">
            <p className="empty-hint">
              Ask a question about your indexed documents.
            </p>
            <div className="suggested-prompts">
              {SUGGESTED_PROMPTS.map((prompt, i) => (
                <button
                  key={i}
                  className="suggested-prompt"
                  onClick={() => { setInput(prompt); }}
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((msg, idx) => {
          const hasCitations =
            msg.role === "assistant" &&
            msg.citations &&
            msg.citations.length > 0;
          const { answer, steps } = msg.role === "assistant"
            ? parseReasoning(msg.content)
            : { answer: msg.content, steps: [] as string[] };
          const hasReasoning = steps.length > 0;
          const displayText = hasReasoning ? answer : msg.content;

          return (
            <div key={idx} className={`message message-${msg.role}`}>
              <span className="message-role">
                {msg.role === "user" ? "You" : "Assistant"}
                {msg.role === "assistant" && (
                  <span className={`response-type-badge ${hasReasoning ? "badge-reasoned" : "badge-factual"}`}>
                    {hasReasoning ? "🔍 Reasoned answer" : "📖 Factual answer"}
                  </span>
                )}
              </span>
              <p className="message-content">
                {hasCitations
                  ? renderWithCitations(displayText, msg.citations!, (citIdx) =>
                      setActiveCitation(
                        activeCitation?.msgIdx === idx &&
                          activeCitation?.citIdx === citIdx
                          ? null
                          : { msgIdx: idx, citIdx },
                      ),
                    )
                  : displayText}
              </p>
              {hasReasoning && (
                <div className="reasoning-section">
                  <button
                    className="reasoning-toggle"
                    onClick={() => toggleReasoning(idx)}
                  >
                    {expandedReasoning.has(idx)
                      ? "▾ Hide reasoning steps"
                      : "▸ Show reasoning steps"}
                  </button>
                  {expandedReasoning.has(idx) && (
                    <ol className="reasoning-steps">
                      {steps.map((step, si) => (
                        <li key={si} className="reasoning-step">
                          <span className="reasoning-step-text">
                            {hasCitations
                              ? renderWithCitations(
                                  step,
                                  msg.citations!,
                                  (citIdx) =>
                                    setActiveCitation(
                                      activeCitation?.msgIdx === idx &&
                                        activeCitation?.citIdx === citIdx
                                        ? null
                                        : { msgIdx: idx, citIdx },
                                    ),
                                )
                              : step}
                          </span>
                          <button
                            className="step-ask-btn"
                            title={`Ask about step ${si + 1}`}
                            onClick={() => prefillStep(si + 1)}
                          >
                            Ask about this step
                          </button>
                        </li>
                      ))}
                    </ol>
                  )}
                </div>
              )}
              {msg.citations && (
                <CitationList
                  citations={msg.citations}
                  activeIdx={
                    activeCitation?.msgIdx === idx
                      ? activeCitation.citIdx
                      : null
                  }
                  onSelect={(citIdx) =>
                    setActiveCitation(
                      activeCitation?.msgIdx === idx &&
                        activeCitation?.citIdx === citIdx
                        ? null
                        : { msgIdx: idx, citIdx },
                    )
                  }
                />
              )}
              {msg.role === "assistant" && (
                <div className="feedback-bar">
                  {feedbackGiven.has(idx) ? (
                    <span className="feedback-thanks">
                      {feedbackGiven.get(idx) === "up" ? "👍" : "👎"} Thanks for your feedback
                    </span>
                  ) : (
                    <>
                      <span className="feedback-label">Was this helpful?</span>
                      <button
                        className="feedback-btn feedback-up"
                        title="Thumbs up"
                        disabled={feedbackSending}
                        onClick={() => void handleFeedback(idx, "up")}
                      >
                        👍
                      </button>
                      <button
                        className="feedback-btn feedback-down"
                        title="Thumbs down"
                        disabled={feedbackSending}
                        onClick={() => void handleFeedback(idx, "down")}
                      >
                        👎
                      </button>
                      <button
                        className="feedback-btn feedback-suggest-btn"
                        onClick={() => setSuggestionOpen(suggestionOpen === idx ? null : idx)}
                      >
                        Suggest better answer
                      </button>
                    </>
                  )}
                  {suggestionOpen === idx && !feedbackGiven.has(idx) && (
                    <div className="feedback-suggestion">
                      <textarea
                        className="feedback-suggestion-input"
                        placeholder="What would be a better answer?"
                        value={suggestionText}
                        onChange={(e) => setSuggestionText(e.target.value)}
                        rows={3}
                      />
                      <div className="feedback-suggestion-actions">
                        <button
                          className="feedback-suggestion-submit"
                          disabled={feedbackSending || !suggestionText.trim()}
                          onClick={() => void handleSuggestionSubmit(idx)}
                        >
                          Submit suggestion
                        </button>
                        <button
                          className="feedback-suggestion-cancel"
                          onClick={() => { setSuggestionOpen(null); setSuggestionText(""); }}
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
        {loading && (
          <div className="message message-assistant">
            <span className="message-role">Assistant</span>
            <p className="message-content typing">Thinking…</p>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="input-row">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question… (Enter to send, Shift+Enter for newline)"
          disabled={loading}
          rows={3}
        />
        <button onClick={handleSend} disabled={loading || !input.trim()}>
          Send
        </button>
      </div>
    </div>
  );
}
