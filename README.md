# rag-demo

A minimal, well-engineered Retrieval-Augmented Generation (RAG) application.

**Stack:** Python 3.11+ / FastAPI · React + TypeScript (Vite) · Qdrant (Docker) · Azure OpenAI

---

## Quick Start

### Prerequisites

- Docker + Docker Compose
- Python 3.11+
- Node.js 18+
- An Azure OpenAI (or OpenAI) API key

### 1. Configure environment

```bash
cp .env.example .env
# Edit .env and fill in your Azure OpenAI keys
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

1. Open the frontend at http://localhost:5173.
2. Use the **Upload** panel to select a PDF, DOCX, or TXT file.
3. The file is saved to `documents/uploads/` and indexed automatically.

### Chat

Type your question in the chat box. Each assistant response includes a **Sources** section listing the documents and page/section references used to generate the answer.

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

- **112 tests** across 13 test files
- 100% statement coverage (519/519 statements)
- Tests cover all API endpoints, loaders (PDF, DOCX, TXT), chunking, indexing, search, and vector store operations

### Frontend tests

```bash
cd src/fe
npm test
```

- **41 tests** across 5 test files
- 100% coverage (statements, branches, functions, lines)
- Tests cover all components (`ChatPanel`, `UploadPanel`, `CitationList`, `App`) and the API client

To see a detailed coverage report:

```bash
cd src/fe
npx vitest run --coverage
```

---

## Database (Qdrant)

Qdrant is the vector database used to store document embeddings. **No manual database setup is required** — everything is automatic:

1. **`docker compose up -d`** starts an empty Qdrant server (v1.13.2) on ports 6333/6334. No collections or data exist yet.
2. **On first upload or reindex**, the backend calls `init_collection()` which checks if the collection exists and creates it automatically with the correct vector dimensions and cosine distance metric.
3. **Data persists** in the `data/qdrant/` directory (a Docker volume mount). This directory is gitignored, so each developer starts with a fresh database.
4. **After a restart**, Qdrant reloads from `data/qdrant/` — no need to reindex unless you've deleted that directory.

The collection name defaults to `rag_docs` and can be changed via the `QDRANT_COLLECTION` environment variable in `.env`.

To **fully reset** the database, stop the container and delete the data directory:

```bash
docker compose down
rm -rf data/qdrant
docker compose up -d
# Then reindex your documents
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

The chat endpoint returns a `citations` list alongside every answer. The frontend renders each citation with the source file name, page/section, and a short snippet.

---

## Adding new documents

Drop PDF, DOCX, or TXT files into the `documents/` folder and run reindex:

```bash
bash scripts/reindex.sh
```

---

## Swapping the vector store

The `VectorStore` abstract interface lives in `src/be/app/vectordb/base.py`. To swap Qdrant for another backend (e.g. **Oracle AI Vector Search**):

1. Create a new file, e.g. `src/be/app/vectordb/oracle_store.py`, implementing `VectorStore`.
2. Update the dependency in `src/be/app/main.py` to instantiate your new class.
3. Add connection settings to `.env.example` and `config.py`.

All other application code remains unchanged.

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `Azure keys missing` error | Fill `AZURE_OPENAI_*` values in `.env` |
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
