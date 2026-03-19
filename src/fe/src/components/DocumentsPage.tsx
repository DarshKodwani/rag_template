import { useState, useRef, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import {
  uploadFile,
  reindexStream,
  listDocuments,
} from "../api/client";
import type { DocumentInfo, IngestResponse } from "../types";

export function DocumentsPage() {
  const [docs, setDocs] = useState<DocumentInfo[]>([]);
  const [showDocs, setShowDocs] = useState(false);
  const [docsError, setDocsError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [progress, setProgress] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const fetchDocs = useCallback(async () => {
    try {
      setDocsError(null);
      const data = await listDocuments();
      setDocs(data);
    } catch {
      setDocsError("Failed to load document list.");
    }
  }, []);

  useEffect(() => {
    void fetchDocs();
  }, [fetchDocs]);

  async function handleUpload() {
    const file = fileRef.current?.files?.[0];
    if (!file) return;
    setLoading(true);
    setStatus(null);
    try {
      const res: IngestResponse = await uploadFile(file);
      setStatus(
        res.status === "ok"
          ? `✅ Indexed ${res.indexed} chunk(s) from "${file.name}"`
          : `⚠️ Partial: ${res.errors.join("; ")}`,
      );
      void fetchDocs();
    } catch (err: unknown) {
      setStatus(`❌ Upload failed: ${String(err)}`);
    } finally {
      setLoading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  function handleReindex() {
    setLoading(true);
    setStatus(null);
    setProgress("Starting reindex…");

    reindexStream(
      (event) => {
        if (event.type === "progress") {
          setProgress(
            `Indexing ${event.doc_name} (${event.current}/${event.total})…`,
          );
        } else if (event.type === "done") {
          setStatus(
            `✅ Reindexed ${event.indexed} chunk(s)` +
              ((event.errors as string[])?.length
                ? ` — ${(event.errors as string[]).join("; ")}`
                : ""),
          );
          setProgress(null);
          void fetchDocs();
        } else if (event.type === "error") {
          setStatus(`❌ ${event.message}`);
          setProgress(null);
        }
      },
      () => setLoading(false),
      (err) => {
        setStatus(`❌ Reindex failed: ${err}`);
        setProgress(null);
        setLoading(false);
      },
    );
  }

  return (
    <div className="documents-page">
      <div className="documents-header">
        <Link to="/" className="back-link">← Home</Link>
        <h2>Manage Documents</h2>
      </div>

      {/* Upload section */}
      <section className="documents-section">
        <h3>Upload a document</h3>
        <div className="upload-row">
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,.docx,.txt"
            disabled={loading}
          />
          <button onClick={handleUpload} disabled={loading}>
            {loading ? "Working…" : "Upload & Index"}
          </button>
        </div>
      </section>

      {/* Reindex section */}
      <section className="documents-section">
        <h3>Re-index all documents</h3>
        <p className="section-desc">
          Scans the <code>documents/</code> folder and re-indexes every file.
        </p>
        <button
          onClick={handleReindex}
          disabled={loading}
          className="reindex-btn"
        >
          {loading ? "Working…" : "🔄 Reindex All"}
        </button>
        {progress && <p className="progress-text">{progress}</p>}
      </section>

      {/* Status */}
      {status && <p className="upload-status">{status}</p>}
      {docsError && <p className="upload-status">❌ {docsError}</p>}

      {/* Indexed documents */}
      <section className="documents-section">
        <button
          className="docs-toggle"
          onClick={() => setShowDocs((prev) => !prev)}
        >
          📋 {showDocs ? "Hide" : "View"} indexed documents ({docs.length})
        </button>

        {showDocs && (
          <div className="docs-list">
            {docs.length === 0 ? (
              <p className="empty-hint">No documents indexed yet.</p>
            ) : (
              <table className="docs-table">
                <thead>
                  <tr>
                    <th>Document</th>
                    <th>Chunks</th>
                    <th>Indexed at</th>
                  </tr>
                </thead>
                <tbody>
                  {docs.map((d) => (
                    <tr key={d.doc_id}>
                      <td>{d.doc_name}</td>
                      <td>{d.chunks}</td>
                      <td>
                        {new Date(d.indexed_at).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
