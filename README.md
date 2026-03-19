# AnaGuide

AnaCredit regulation assistant for BIL (Banque Internationale à Luxembourg), built on a Retrieval-Augmented Generation (RAG) architecture.

**Stack:** Python 3.13 / FastAPI · React 19 + TypeScript (Vite) · Qdrant (Docker) · OpenAI gpt-4o

---

## Features

- **Chat with citations** — ask questions about AnaCredit regulation and get LLM answers grounded in your indexed documents, with inline source references
- **Reasoning chain** — collapsible "reasoning" section shows the retrieval and generation steps behind each answer
- **Document management** — upload PDF / DOCX / TXT files, view indexed documents, and reindex with streaming progress
- **Feedback system** — thumbs up/down on every answer, stored in SQLite with an admin listing endpoint
- **Benchmark framework** — 50-question ground truth set, automated scoring (ROUGE / keyword / LLM-judge), HTML dashboard
- **Suggested prompts** — curated starter questions displayed on the landing page and in the chat panel

---

## Quick Start

### Prerequisites

- Docker + Docker Compose
- Python 3.11+
- Node.js 18+
- An OpenAI (or Azure OpenAI) API key

### 1. Configure environment

```bash
cp .env.example .env
# Edit .env and set OPENAI_API_KEY (or Azure OpenAI keys)
```

### 2. Start everything

```bash
bash scripts/dev.sh
```

This starts Qdrant (Docker), the FastAPI backend (port 8000), and the React frontend (port 5173) in one command.

**Or start each service manually:**

```bash
# Terminal 1 – Qdrant
docker compose up -d

# Terminal 2 – Backend
cd src/be
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000

# Terminal 3 – Frontend
cd src/fe
npm install
npm run dev
```

- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs
- Frontend: http://localhost:5173

---

## Usage

### Upload a document

1. Open the frontend at http://localhost:5173 and navigate to **Manage Documents**.
2. Select a PDF, DOCX, or TXT file and click **Upload & Index**.
3. The file is saved to `documents/uploads/` and indexed automatically.

### Chat

Navigate to the **Chat** page. Type your question or select a suggested prompt. Each response includes:

- A **Sources** panel with document citations (file, page/section, snippet)
- A collapsible **Reasoning** section showing retrieval details
- A **Feedback** button (👍/👎) to rate the answer

### Reindex all documents

```bash
bash scripts/reindex.sh
```

This re-reads everything in the `documents/` directory (including `documents/uploads/`) and rebuilds the Qdrant index.

---

## Testing

Both backend and frontend have **100% test coverage**.

### Backend tests

```bash
cd src/be
source .venv/bin/activate
pytest ../../tests/be/ --cov=app --cov-report=term-missing
```

- **220 tests** across 17 test files
- 100% statement coverage (898 statements)
- Covers API endpoints, loaders, chunking, indexing, search, vector store, feedback, benchmarks, and citations

### Frontend tests

```bash
cd src/fe
npm test
```

- **90 tests** across 7 test files
- 100% coverage (statements, branches, functions, lines)
- Covers all components, routing, API client, and user interactions

To see a detailed coverage report:

```bash
cd src/fe
npx vitest run --coverage
```

---

## Database (Qdrant)

Qdrant is the vector database used to store document embeddings. **No manual database setup is required** — everything is automatic:

1. **`docker compose up -d`** starts an empty Qdrant server (v1.13.2) on ports 6333/6334.
2. **On first upload or reindex**, the backend calls `init_collection()` which creates the collection with the correct vector dimensions and cosine distance metric.
3. **Data persists** in the `data/qdrant/` directory (a Docker volume mount). This directory is gitignored.
4. **After a restart**, Qdrant reloads from `data/qdrant/` — no need to reindex unless you've deleted that directory.

The collection name defaults to `documents` and can be changed via `QDRANT_COLLECTION` in `.env`.

To **fully reset** the database:

```bash
docker compose down
rm -rf data/qdrant
docker compose up -d
bash scripts/reindex.sh
```

---

## How citations work

When a document is indexed each text chunk is stored in Qdrant with metadata:

| Field | Description |
|---|---|
| `doc_name` | File name |
| `doc_rel_path` | Relative path from repo root |
| `page` | PDF page number (1-based) |
| `section` | DOCX heading / paragraph index |
| `start_offset` | Character start offset inside the document |
| `end_offset` | Character end offset |
| `text` | The chunk text itself |

The chat endpoint returns a `citations` list alongside every answer. The frontend renders each citation with the source file, page/section, and a short snippet.

---

## Benchmarks

A 50-question ground truth set is located in `benchmarks/ground_truth.json`. To run:

```bash
cd src/be
source .venv/bin/activate
python -m app.benchmark.runner
```

This produces `benchmarks/latest_report.json` and an HTML dashboard at `benchmarks/dashboard.html`. Scoring uses ROUGE-L, keyword overlap, and LLM-as-judge metrics.

---

## Feedback

The `/feedback` API stores user ratings in SQLite (`data/feedback.db`). Endpoints:

| Method | Path | Description |
|---|---|---|
| POST | `/feedback` | Submit a rating (up/down) with optional suggested answer |
| GET | `/feedback` | List feedback entries with pagination and rating filter |

---

## Swapping the vector store

The `VectorStore` abstract interface lives in `src/be/app/vectordb/base.py`. To swap Qdrant for another backend:

1. Create a new file implementing `VectorStore` (e.g. `oracle_store.py`).
2. Update `src/be/app/main.py` to instantiate your new class.
3. Add connection settings to `.env.example` and `config.py`.

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `LLM service not configured` | Set `OPENAI_API_KEY` (or Azure keys) in `.env` |
| Qdrant connection refused | Run `docker compose up -d` |
| Empty answers | Upload & reindex documents first |
| Frontend can't reach backend | Ensure backend is running on port 8000 |

---

## Windows users

`scripts/dev.sh` is a Bash script. On Windows run each command individually:

```powershell
docker compose up -d
cd src\be && .venv\Scripts\activate && uvicorn app.main:app --reload --port 8000
cd src\fe && npm run dev
```
