import { useChat } from "../hooks/useChat";
import { ChatInput } from "./ChatInput";
import { ErrorBanner } from "./ErrorBanner";
import { MessageList } from "./MessageList";
import { SourcesPanel } from "./SourcesPanel";

const SUGGESTIONS = [
  "3-bedroom apartments for sale in Riyadh under 2M",
  "Luxury DarGlobal villas in the UAE",
  "Cheapest apartments for rent in Jeddah",
  "Which projects have direct beach access?",
];

export function ChatWindow() {
  const { messages, sources, isStreaming, error, send, stop } = useChat();
  const lastUser = [...messages].reverse().find((m) => m.role === "user");

  return (
    <div className="chat-layout">
      <main className="chat-main">
        {messages.length === 0 ? (
          <div className="empty-state">
            <h1>🏠 Real Estate Assistant</h1>
            <p>
              Ask about luxury <strong>DarGlobal</strong> developments and{" "}
              <strong>Wasalt</strong> listings across Saudi Arabia. Answers are
              grounded in scraped public listing data.
            </p>
            <div className="suggestions">
              {SUGGESTIONS.map((s) => (
                <button key={s} className="chip" onClick={() => send(s)}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <MessageList messages={messages} isStreaming={isStreaming} />
        )}

        {error && (
          <ErrorBanner
            message={error}
            onRetry={lastUser ? () => send(lastUser.content) : undefined}
          />
        )}

        <ChatInput onSend={send} onStop={stop} isStreaming={isStreaming} />
      </main>

      <SourcesPanel sources={sources} />
    </div>
  );
}
