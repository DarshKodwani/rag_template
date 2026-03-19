import { useRef, useEffect } from "react";
import type { Citation } from "../types";
import { docUrl } from "../api/client";

interface Props {
  citations: Citation[];
  activeIdx: number | null;
  onSelect: (idx: number) => void;
}

export function CitationList({ citations, activeIdx, onSelect }: Props) {
  const popoverRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (activeIdx === null) return;
    function handleClick(e: MouseEvent) {
      if (
        popoverRef.current &&
        !popoverRef.current.contains(e.target as Node)
      ) {
        onSelect(activeIdx!);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [activeIdx, onSelect]);

  if (citations.length === 0) return null;

  const activeCitation = activeIdx !== null ? citations[activeIdx] : null;

  return (
    <div className="citations">
      <p className="citations-header">Sources</p>
      <div className="citation-chips">
        {citations.map((c, idx) => (
          <button
            key={c.chunk_id}
            className={`citation-chip ${activeIdx === idx ? "citation-chip--active" : ""}`}
            onClick={() => onSelect(idx)}
            title={c.doc_name}
          >
            <span className="citation-chip-num">{idx + 1}</span>
            <span className="citation-chip-name">{c.doc_name}</span>
          </button>
        ))}
      </div>

      {activeCitation && (
        <div className="citation-popover" ref={popoverRef}>
          <div className="citation-popover-header">
            <a
              href={docUrl(activeCitation.doc_path)}
              target="_blank"
              rel="noreferrer"
              className="citation-popover-title"
            >
              📄 {activeCitation.doc_name}
            </a>
            <button
              className="citation-popover-close"
              onClick={() => onSelect(activeIdx!)}
              aria-label="Close"
            >
              ×
            </button>
          </div>
          <div className="citation-popover-meta">
            {activeCitation.page != null && (
              <span className="citation-tag">Page {activeCitation.page}</span>
            )}
            {activeCitation.section && (
              <span className="citation-tag">§ {activeCitation.section}</span>
            )}
          </div>
          <blockquote className="citation-popover-snippet">
            {activeCitation.snippet}
          </blockquote>
        </div>
      )}
    </div>
  );
}
