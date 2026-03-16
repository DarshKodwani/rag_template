# bil-anacredit-rag-demo

A minimal, well-engineered Retrieval-Augmented Generation (RAG) application.

**Stack:** Python 3.11+ / FastAPI · React + TypeScript (Vite) · Qdrant (Docker) · Azure OpenAI

---

## Quick Start

### 1. Prerequisites

- Docker + Docker Compose
- Python 3.11+
- Node.js 18+

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and fill in your Azure OpenAI keys
```

### 3. Start Qdrant

```bash
docker compose up -d
```

### 4. Run the backend

```bash
cd src/be
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

Backend API: http://localhost:8000  
API docs: http://localhost:8000/docs

### 5. Run the frontend

```bash
cd src/fe
npm install
npm run dev
```

Frontend: http://localhost:5173

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
# Via script
bash scripts/reindex.sh

# Or directly
curl -X POST http://localhost:8000/ingest/reindex
```

This re-reads everything in the `documents/` directory (including `documents/uploads/`) and rebuilds the Qdrant index.

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