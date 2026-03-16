#!/usr/bin/env bash
# scripts/reindex.sh — Trigger a full reindex of the documents/ directory.
set -euo pipefail

BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"

echo "==> Triggering reindex on $BACKEND_URL ..."
curl -sf -X POST "$BACKEND_URL/ingest/reindex" \
  -H "Content-Type: application/json" | python3 -m json.tool
