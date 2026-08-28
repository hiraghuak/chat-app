import { useState, KeyboardEvent } from "react";

interface Props {
  onSend: (text: string) => void;
  onStop: () => void;
  isStreaming: boolean;
}

export function ChatInput({ onSend, onStop, isStreaming }: Props) {
  const [text, setText] = useState("");

  const submit = () => {
    if (!text.trim() || isStreaming) return;
    onSend(text);
    setText("");
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="chat-input">
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={onKeyDown}
        placeholder="Ask about properties — e.g. '3-bedroom apartments for sale in Riyadh under 2M'"
        rows={1}
        disabled={isStreaming}
      />
      {isStreaming ? (
        <button className="btn stop" onClick={onStop}>Stop</button>
      ) : (
        <button className="btn send" onClick={submit} disabled={!text.trim()}>
          Send
        </button>
      )}
    </div>
  );
}
