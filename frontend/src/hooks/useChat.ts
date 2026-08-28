import { useCallback, useRef, useState } from "react";
import { streamChat } from "../api/chatStream";
import type { ChatMessage, Source } from "../types";

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const stop = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const send = useCallback(
    async (text: string) => {
      const content = text.trim();
      if (!content || isStreaming) return;

      setError(null);
      setSources([]);
      const history: ChatMessage[] = [...messages, { role: "user", content }];
      // Optimistically add the user message + an empty assistant placeholder.
      setMessages([...history, { role: "assistant", content: "" }]);
      setIsStreaming(true);

      const controller = new AbortController();
      abortRef.current = controller;

      const appendToAssistant = (chunk: string) =>
        setMessages((prev) => {
          const next = [...prev];
          const last = next[next.length - 1];
          if (last?.role === "assistant") {
            next[next.length - 1] = { ...last, content: last.content + chunk };
          }
          return next;
        });

      try {
        await streamChat(history, {
          signal: controller.signal,
          onFrame: (frame) => {
            switch (frame.type) {
              case "sources":
                setSources(frame.listings);
                break;
              case "delta":
                appendToAssistant(frame.content);
                break;
              case "error":
                setError(frame.message);
                break;
              case "done":
                break;
            }
          },
        });
      } catch (err) {
        if ((err as Error)?.name !== "AbortError") {
          setError("Unable to reach the server. Please check your connection and try again.");
        }
      } finally {
        setIsStreaming(false);
        abortRef.current = null;
        // Drop a trailing empty assistant bubble (e.g. immediate error/abort).
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last?.role === "assistant" && last.content === "") return prev.slice(0, -1);
          return prev;
        });
      }
    },
    [messages, isStreaming],
  );

  return { messages, sources, isStreaming, error, send, stop };
}
