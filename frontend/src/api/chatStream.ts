import type { ChatMessage, SSEFrame } from "../types";

/**
 * Split a buffer of accumulated SSE text into complete frames + the remainder.
 * A single network chunk may split a frame, or contain several — callers must
 * carry `rest` forward. Exported as a pure function so it can be unit-tested.
 */
export function splitSSE(buffer: string): { frames: SSEFrame[]; rest: string } {
  const frames: SSEFrame[] = [];
  const parts = buffer.split("\n\n");
  const rest = parts.pop() ?? ""; // last piece may be incomplete
  for (const part of parts) {
    const line = part.split("\n").find((l) => l.startsWith("data:"));
    if (!line) continue;
    const json = line.slice(5).trim();
    if (!json) continue;
    try {
      frames.push(JSON.parse(json) as SSEFrame);
    } catch {
      // ignore malformed frame
    }
  }
  return { frames, rest };
}

export interface StreamHandlers {
  onFrame: (frame: SSEFrame) => void;
  signal?: AbortSignal;
}

/** POST the conversation and dispatch each SSE frame as it arrives. */
export async function streamChat(
  messages: ChatMessage[],
  { onFrame, signal }: StreamHandlers,
): Promise<void> {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages }),
    signal,
  });

  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      /* keep default */
    }
    onFrame({ type: "error", message: detail });
    return;
  }

  const reader = res.body?.getReader();
  if (!reader) {
    onFrame({ type: "error", message: "Streaming is not supported by this browser." });
    return;
  }

  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const { frames, rest } = splitSSE(buffer);
    buffer = rest;
    for (const frame of frames) onFrame(frame);
  }
}
