import React, { useState, useEffect, useRef } from "react";

const API_BASE = "http://localhost:8000";

interface Source {
  filename?: string;
  chunk_index?: number;
  score?: number;
  text?: string;
}

interface Message {
  id: string;
  role: "user" | "assistant";
  text: string;
  sources?: Source[];
}

const UserChat: React.FC = () => {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);

  const chatRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight;
    }
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const q = input.trim();
    setInput("");

    const userMsg: Message = {
      id: Date.now() + "-u",
      role: "user",
      text: q,
    };
    setMessages((prev) => [...prev, userMsg]);

    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/user/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ q }),
      });

      const data = await res.json();

      const assistantMsg: Message = {
        id: Date.now() + "-a",
        role: "assistant",
        text: data.answer || "No answer.",
        sources: data.sources || [],
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (error: any) {
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + "-err",
          role: "assistant",
          text: "Error: " + error.message,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      <h2 style={styles.heading}>Ask your documents</h2>

      <div style={styles.chatBox}>
        {/* Chat messages */}
        <div ref={chatRef} style={styles.messages}>
          {messages.map((m) => (
            <div
              key={m.id}
              style={m.role === "user" ? styles.userMessage : styles.assistantMessage}
            >
              <div style={styles.msgText}>{m.text}</div>

              {/* Sources */}
              {m.role === "assistant" && m.sources && m.sources.length > 0 && (
                <div style={styles.sources}>
                  <strong>Sources:</strong>
                  <ul>
                    {m.sources.map((s, i) => (
                      <li key={i}>
                        <small>
                          {s.filename} (chunk {s.chunk_index}) — score{" "}
                          {s.score?.toFixed(3)}
                        </small>
                        <div style={styles.snippet}>
                          {s.text?.slice(0, 250)}...
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Input section */}
        <div>
          <textarea
            style={styles.textarea}
            placeholder="Ask a question..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
          ></textarea>

          <div style={styles.controls}>
            <button
              style={styles.button}
              onClick={sendMessage}
              disabled={loading || !input.trim()}
            >
              {loading ? "Thinking..." : "Send"}
            </button>

            <button
              style={styles.clearButton}
              onClick={() => setMessages([])}
            >
              Clear
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default UserChat;

/* ----------------------- INLINE STYLES ----------------------- */

const styles: Record<string, React.CSSProperties> = {
  container: {
    maxWidth: "800px",
    margin: "0 auto",
    padding: "20px",
    fontFamily: "Arial, sans-serif",
  },
  heading: {
    marginBottom: "15px",
    fontSize: "22px",
    fontWeight: 600,
  },
  chatBox: {
    border: "1px solid #ddd",
    borderRadius: "10px",
    padding: "15px",
    background: "#fafafa",
  },
  messages: {
    maxHeight: "450px",
    overflowY: "auto",
    padding: "10px",
    display: "flex",
    flexDirection: "column",
    gap: "12px",
    background: "#ffffff",
    borderRadius: "8px",
    border: "1px solid #eee",
  },
  userMessage: {
    alignSelf: "flex-end",
    background: "#dcf8ff",
    padding: "10px",
    borderRadius: "10px",
    maxWidth: "70%",
    border: "1px solid #b3e4ff",
  },
  assistantMessage: {
    alignSelf: "flex-start",
    background: "#f1f3f4",
    padding: "10px",
    borderRadius: "10px",
    maxWidth: "70%",
    border: "1px solid #ddd",
  },
  msgText: {
    fontSize: "14px",
    marginBottom: "5px",
    whiteSpace: "pre-wrap",
    lineHeight: "1.4",
  },
  sources: {
    marginTop: "8px",
    fontSize: "12px",
  },
  snippet: {
    background: "#fff",
    padding: "6px",
    borderRadius: "6px",
    border: "1px solid #eee",
    marginTop: "4px",
    fontSize: "12px",
    color: "#555",
  },
  textarea: {
    width: "100%",
    minHeight: "80px",
    marginTop: "10px",
    padding: "10px",
    fontSize: "14px",
    borderRadius: "8px",
    border: "1px solid #ccc",
    resize: "vertical",
  },
  controls: {
    marginTop: "10px",
    display: "flex",
    gap: "10px",
  },
  button: {
    padding: "10px 16px",
    background: "#0077ff",
    color: "#fff",
    border: "none",
    borderRadius: "6px",
    cursor: "pointer",
  },
  clearButton: {
    padding: "10px 16px",
    background: "#d9534f",
    color: "#fff",
    border: "none",
    borderRadius: "6px",
    cursor: "pointer",
  },
};
