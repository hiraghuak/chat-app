import ReactMarkdown from "react-markdown";
import type { ChatMessage } from "../types";

// react-markdown is used WITHOUT rehype-raw, so raw HTML in model output or
// scraped text is never rendered — this prevents XSS from injected content.
export function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={`bubble-row ${isUser ? "user" : "assistant"}`}>
      <div className="avatar">{isUser ? "🧑" : "🏠"}</div>
      <div className={`bubble ${isUser ? "user" : "assistant"}`}>
        {isUser ? (
          <span className="plain">{message.content}</span>
        ) : (
          <ReactMarkdown
            components={{
              a: ({ node, ...props }) => (
                <a {...props} target="_blank" rel="noopener noreferrer" />
              ),
            }}
          >
            {message.content}
          </ReactMarkdown>
        )}
      </div>
    </div>
  );
}
