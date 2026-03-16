import { useState, useRef, useEffect } from "react";
import { sendChat } from "../api/client";
import type { UIMessage } from "../types";
import { CitationList } from "./CitationList";

export function ChatPanel() {
  const [messages, setMessages] = useState<UIMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

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
      <h2>Chat</h2>
      <div className="message-list">
        {messages.length === 0 && (
          <p className="empty-hint">Upload documents, then ask a question.</p>
        )}
        {messages.map((msg, idx) => (
          <div key={idx} className={`message message-${msg.role}`}>
            <span className="message-role">
              {msg.role === "user" ? "You" : "Assistant"}
            </span>
            <p className="message-content">{msg.content}</p>
            {msg.citations && <CitationList citations={msg.citations} />}
          </div>
        ))}
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
