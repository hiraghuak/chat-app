import { describe, expect, it } from "vitest";
import { splitSSE } from "./chatStream";

describe("splitSSE", () => {
  it("parses multiple complete frames in one buffer", () => {
    const buf =
      'data: {"type":"delta","content":"Hello"}\n\n' +
      'data: {"type":"delta","content":" world"}\n\n';
    const { frames, rest } = splitSSE(buf);
    expect(frames).toHaveLength(2);
    expect(frames[0]).toEqual({ type: "delta", content: "Hello" });
    expect(rest).toBe("");
  });

  it("carries an incomplete trailing frame forward in rest", () => {
    const buf = 'data: {"type":"delta","content":"Hi"}\n\ndata: {"type":"de';
    const { frames, rest } = splitSSE(buf);
    expect(frames).toHaveLength(1);
    expect(rest).toBe('data: {"type":"de');
  });

  it("reassembles a frame split across two chunks", () => {
    const first = splitSSE('data: {"type":"del');
    expect(first.frames).toHaveLength(0);
    const second = splitSSE(first.rest + 'ta","content":"X"}\n\n');
    expect(second.frames).toEqual([{ type: "delta", content: "X" }]);
  });

  it("parses sources and error frames", () => {
    const buf =
      'data: {"type":"sources","listings":[]}\n\n' +
      'data: {"type":"error","message":"boom"}\n\n';
    const { frames } = splitSSE(buf);
    expect(frames[0].type).toBe("sources");
    expect(frames[1]).toEqual({ type: "error", message: "boom" });
  });

  it("ignores malformed JSON without throwing", () => {
    const { frames } = splitSSE("data: {not json}\n\n");
    expect(frames).toHaveLength(0);
  });
});
