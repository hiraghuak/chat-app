export type Role = "user" | "assistant";

export interface ChatMessage {
  role: Role;
  content: string;
}

export interface Source {
  id: string;
  title: string;
  source: "DarGlobal" | "Wasalt";
  city?: string | null;
  country?: string | null;
  price?: number | null;
  currency?: string | null;
  property_type?: string | null;
  listing_type?: string | null;
  url?: string | null;
}

// Frames emitted by the backend SSE stream.
export type SSEFrame =
  | { type: "sources"; listings: Source[] }
  | { type: "delta"; content: string }
  | { type: "done"; finish_reason?: string }
  | { type: "error"; message: string };
