import { useEffect, useRef } from "react";
import type { ChatMessage } from "../types";
import { MessageBubble } from "./MessageBubble";

interface Props {
  messages: ChatMessage[];
  isStreaming: boolean;
}

export function MessageList({ messages, isStreaming }: Props) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const last = messages[messages.length - 1];
  const showTyping = isStreaming && last?.role === "assistant" && last.content === "";

  return (
    <div className="message-list">
      {messages.map((m, i) => (
        <MessageBubble key={i} message={m} />
      ))}
      {showTyping && (
        <div className="bubble-row assistant">
          <div className="avatar">🏠</div>
          <div className="bubble assistant typing">
            <span></span><span></span><span></span>
          </div>
        </div>
      )}
      <div ref={endRef} />
    </div>
  );
}
