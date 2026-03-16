#!/usr/bin/env bash
# scripts/dev.sh — Start all services for local development.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> Starting Qdrant via Docker Compose..."
docker compose -f "$REPO_ROOT/docker-compose.yml" up -d

echo "==> Starting backend..."
cd "$REPO_ROOT/src/be"
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
  .venv/bin/pip install -e ".[dev]" -q
fi
.venv/bin/uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!
echo "   Backend PID: $BACKEND_PID"

echo "==> Starting frontend..."
cd "$REPO_ROOT/src/fe"
if [ ! -d "node_modules" ]; then
  npm install
fi
npm run dev &
FRONTEND_PID=$!
echo "   Frontend PID: $FRONTEND_PID"

echo ""
echo "==> All services started!"
echo "   Backend:  http://localhost:8000"
echo "   Frontend: http://localhost:5173"
echo "   API docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop everything."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; docker compose -f '$REPO_ROOT/docker-compose.yml' stop" EXIT INT TERM
wait
