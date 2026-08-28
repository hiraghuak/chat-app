import type { Source } from "../types";

function formatPrice(s: Source): string {
  if (!s.price) return "On request";
  return `${s.price.toLocaleString()} ${s.currency ?? ""}`.trim();
}

export function SourcesPanel({ sources }: { sources: Source[] }) {
  if (sources.length === 0) return null;
  return (
    <aside className="sources-panel">
      <h2>Grounded in {sources.length} listing{sources.length > 1 ? "s" : ""}</h2>
      <ul>
        {sources.map((s) => (
          <li key={s.id} className="source-card">
            <div className="source-head">
              <span className={`tag ${s.source.toLowerCase()}`}>{s.source}</span>
              {s.property_type && <span className="ptype">{s.property_type}</span>}
            </div>
            <a href={s.url ?? "#"} target="_blank" rel="noopener noreferrer" className="source-title">
              {s.title}
            </a>
            <div className="source-meta">
              {[s.city, s.country].filter(Boolean).join(", ")}
            </div>
            <div className="source-price">{formatPrice(s)}</div>
          </li>
        ))}
      </ul>
    </aside>
  );
}
