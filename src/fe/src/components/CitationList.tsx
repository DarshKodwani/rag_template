import type { Citation } from "../types";
import { docUrl } from "../api/client";

interface Props {
  citations: Citation[];
}

export function CitationList({ citations }: Props) {
  if (citations.length === 0) return null;

  return (
    <div className="citations">
      <p className="citations-header">📎 Sources</p>
      <ul>
        {citations.map((c) => (
          <li key={c.chunk_id} className="citation-item">
            <a href={docUrl(c.doc_path)} target="_blank" rel="noreferrer">
              {c.doc_name}
            </a>
            {c.page != null && <span className="citation-meta"> · p.{c.page}</span>}
            {c.section && <span className="citation-meta"> · §{c.section}</span>}
            <blockquote className="citation-snippet">{c.snippet}</blockquote>
          </li>
        ))}
      </ul>
    </div>
  );
}
