import { useState, useRef } from "react";
import { uploadFile, reindexAll } from "../api/client";
import type { IngestResponse } from "../types";

export function UploadPanel() {
  const [status, setStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

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
          : `⚠️ Partial: ${res.errors.join("; ")}`
      );
    } catch (err: unknown) {
      setStatus(`❌ Upload failed: ${String(err)}`);
    } finally {
      setLoading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function handleReindex() {
    setLoading(true);
    setStatus(null);
    try {
      const res: IngestResponse = await reindexAll();
      setStatus(
        res.status === "ok"
          ? `✅ Reindexed ${res.indexed} chunk(s)`
          : `⚠️ Partial: ${res.errors.join("; ")}`
      );
    } catch (err: unknown) {
      setStatus(`❌ Reindex failed: ${String(err)}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="upload-panel">
      <h2>Documents</h2>
      <div className="upload-row">
        <input
          ref={fileRef}
          type="file"
          accept=".pdf,.docx,.txt"
          disabled={loading}
        />
        <button onClick={handleUpload} disabled={loading}>
          {loading ? "Uploading…" : "Upload & Index"}
        </button>
      </div>
      <button onClick={handleReindex} disabled={loading} className="reindex-btn">
        {loading ? "Working…" : "🔄 Reindex All"}
      </button>
      {status && <p className="upload-status">{status}</p>}
    </div>
  );
}
