#!/usr/bin/env bash
# scripts/reindex.sh — Trigger a full reindex of the documents/ directory.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
STARTED_BACKEND=false

# --- Ensure Qdrant is running ------------------------------------------------
if ! docker compose -f "$REPO_ROOT/docker-compose.yml" ps --status running 2>/dev/null | grep -q qdrant; then
  echo "==> Qdrant not running — starting via Docker Compose..."
  docker compose -f "$REPO_ROOT/docker-compose.yml" up -d
fi

# --- Ensure backend is running -----------------------------------------------
if ! curl -sf "$BACKEND_URL/health" > /dev/null 2>&1; then
  echo "==> Backend not running — starting it..."
  cd "$REPO_ROOT/src/be"
  if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    .venv/bin/pip install -e ".[dev]" -q
  fi
  .venv/bin/uvicorn app.main:app --port 8000 &
  BACKEND_PID=$!
  STARTED_BACKEND=true

  # Wait for backend to become healthy
  echo -n "   Waiting for backend"
  for i in $(seq 1 30); do
    if curl -sf "$BACKEND_URL/health" > /dev/null 2>&1; then
      echo " ready!"
      break
    fi
    if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
      echo " failed (process exited)."
      exit 1
    fi
    echo -n "."
    sleep 1
  done

  if ! curl -sf "$BACKEND_URL/health" > /dev/null 2>&1; then
    echo " timed out."
    kill "$BACKEND_PID" 2>/dev/null
    exit 1
  fi
fi

# --- Trigger reindex ----------------------------------------------------------
echo "==> Triggering reindex on $BACKEND_URL ..."
curl -sf -X POST "$BACKEND_URL/ingest/reindex" \
  -H "Content-Type: application/json" | python3 -m json.tool

# --- Clean up if we started the backend ourselves -----------------------------
if [ "$STARTED_BACKEND" = true ]; then
  echo "==> Stopping backend (PID $BACKEND_PID)..."
  kill "$BACKEND_PID" 2>/dev/null
  wait "$BACKEND_PID" 2>/dev/null
fi
