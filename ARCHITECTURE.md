# AnaGuide RAG Architecture

This document describes the system architecture of the AnaGuide Retrieval-Augmented Generation (RAG) application.

## What is RAG?

Retrieval-Augmented Generation (RAG) combines information retrieval with large language models (LLMs) to answer questions grounded in specific documents. Instead of relying solely on an LLM's training data, RAG:

1. **Retrieves** the most relevant documents or passages when given a question
2. **Augments** the LLM prompt with this retrieved context
3. **Generates** a response using both the context and the LLM's reasoning

This approach ensures answers are based on actual source material and reduces hallucination compared to pure LLM inference.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AnaGuide Application                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │             Frontend (React + TypeScript)            │  │
│  │  - Chat interface                                    │  │
│  │  - Document upload                                  │  │
│  │  - Citation display                                 │  │
│  │  - Query routing                                    │  │
│  └──────────────────┬───────────────────────────────────┘  │
│                     │ (HTTP/REST)                           │
│  ┌──────────────────▼───────────────────────────────────┐  │
│  │            Backend (FastAPI/Python)                 │  │
│  │                                                      │  │
│  │  ┌────────────────────────────────────────────────┐ │  │
│  │  │         Chat Orchestrator                      │ │  │
│  │  │  - Receives user queries                       │ │  │
│  │  │  - Manages conversation history                │ │  │
│  │  │  - Routes requests to RAG pipeline             │ │  │
│  │  └────────────────────────────────────────────────┘ │  │
│  │                      │                              │  │
│  │  ┌──────────────────┼──────────────────┐            │  │
│  │  │                  │                  │            │  │
│  │  ▼                  ▼                  ▼            │  │
│  │ ┌────────────┐  ┌────────────┐  ┌──────────────┐  │  │
│  │ │ Ingestion  │  │ Retrieval  │  │ Generation   │  │  │
│  │ │ Pipeline   │  │ Pipeline   │  │ Pipeline     │  │  │
│  │ └────────────┘  └────────────┘  └──────────────┘  │  │
│  │     │               │                │             │  │
│  │     │  Embeddings   │  Query Vector  │ Context +   │  │
│  │     │  + Chunks     │  Search        │ Reasoning   │  │
│  └─────┼───────────────┼────────────────┼─────────────┘  │
│        │               │                │                │
│        │ (gRPC)        │ (HTTP)         │ (HTTP API)     │
│  ┌─────▼───────┐  ┌────▼──────┐  ┌─────▼──────┐        │
│  │   Qdrant    │  │ OpenAI    │  │ Feedback   │        │
│  │ Vector DB   │  │ LLM API   │  │ Database   │        │
│  │             │  │           │  │ (SQLite)   │        │
│  │ - Storage   │  │ - gpt-4o  │  │            │        │
│  │ - Search    │  │ - Emb.3S  │  │ - Ratings  │        │
│  └─────────────┘  └───────────┘  └────────────┘        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Frontend (React + TypeScript + Vite)

The user interface for interacting with the RAG system.

**Responsibilities:**
- Chat interface for asking questions
- Document upload for ingestion
- Citation display linking answers back to source documents
- Conversation history management
- Query routing based on intent

**Key Features:**
- Real-time streaming for document indexing progress
- BIL-branded UI (AnaGuide purple #7B2382)
- Responsive React Router-based navigation
- Type-safe UI components

### 2. Backend (FastAPI / Python 3.13)

The core application logic that orchestrates the RAG pipeline.

**Responsibilities:**
- HTTP API endpoints for chat, ingestion, and feedback
- RAG pipeline orchestration
- Document ingestion and preprocessing
- Query embedding and contextualization
- LLM response generation
- Citation tracking and validation

**Key Modules:**

#### **Chat API** (`app/api/chat.py`)
- `POST /chat` — receives message + chat history, returns LLM response with citations
- Manages conversational context
- Streams responses via Server-Sent Events (SSE)

#### **Ingestion API** (`app/api/ingest.py`)
- `POST /ingest/upload` — uploads documents (PDF, DOCX, TXT)
- `POST /ingest/reindex` — processes all documents into the vector DB
- `GET /ingest/reindex/stream` — streams reindexing progress

#### **Ingestion Pipeline** (`app/rag/indexing.py`)
- Document loading (PDF, DOCX, TXT support)
- Text chunking with overlap
- Vector embedding generation
- Document storage and indexing

#### **Search Pipeline** (`app/rag/search.py`)
- Query embedding
- Similarity search in Qdrant
- Hybrid retrieval (keyword + semantic)
- Top-K retrieval

#### **Generation Pipeline** (`app/rag/citations.py`)
- Context assembly from retrieved chunks
- Prompt engineering with context
- LLM invocation
- Citation extraction and validation

#### **Citation Tracking** (`app/rag/citations.py`)
- Maps LLM citations back to source chunks
- Validates citations against retrieved context
- Prevents hallucinated citations

### 3. Vector Database (Qdrant v1.13.2)

A vector database for storing and searching document embeddings.

**Responsibilities:**
- Store vector embeddings of document chunks
- Perform fast similarity search
- Manage collection schema
- Persist data across restarts

**Design:**
- One collection per ingestion job
- Vectors generated by OpenAI text-embedding-3-small
- gRPC and HTTP APIs supported

### 4. LLM Integration (OpenAI)

**Models Used:**
- **Chat:** `gpt-4o` (reasoning, context understanding, citation)
- **Embeddings:** `text-embedding-3-small` (1536-dim vectors, fast and cost-effective)

**Integration:**
- API-based (no local model hosting)
- Configurable via `.env`
- Streaming support for chat responses

### 5. Feedback & Analytics (SQLite)

Local database for storing user feedback and improving the system.

**Schema:**
- User ratings on answer quality
- Relevance feedback on retrieved chunks
- Citation accuracy feedback

**Storage:**
- File-based SQLite at `data/feedback.db`
- WAL mode for concurrent access
- Structured for analytics

## Data Flow

### 1. Document Ingestion Pipeline

```
User uploads document
         │
         ▼
Document Loader (PDF/DOCX/TXT parser)
         │
         ▼
Text Chunking (fixed-size chunks with overlap)
         │
         ▼
Embedding Generation (OpenAI text-embedding-3-small)
         │
         ▼
Vector Storage (Qdrant collection)
         │
         ▼
Metadata indexing (document ID, chunk position, content preview)
```

**Key Steps:**

1. **Loading:** Extracts text from uploaded documents
   - PDFs: `PyPDF2`
   - DOCX: `python-docx`
   - TXT: Direct text

2. **Chunking:** Splits text into overlapping chunks
   - Default: 1000 tokens per chunk
   - Default: 200 token overlap
   - Preserves semantic coherence

3. **Embedding:** Converts text to vectors
   - OpenAI `text-embedding-3-small`
   - 1536-dimensional vectors
   - Cost-optimized for scale

4. **Storage:** Persists vectors and metadata in Qdrant
   - Enables future retrieval
   - Maintains chunk-to-document mapping

### 2. Query Processing Pipeline

```
User asks a question
         │
         ▼
Query Embedding (OpenAI text-embedding-3-small)
         │
         ▼
Vector Search (Qdrant similarity search)
         │
         ▼
Chunk Retrieval (top-K most similar)
         │
         ▼
Context Assembly (format chunks for LLM)
         │
         ▼
Prompt Engineering (system prompt + context + query)
         │
         ▼
LLM Generation (gpt-4o with reasoning)
         │
         ▼
Citation Extraction (identify which chunks were used)
         │
         ▼
Response Validation (verify citations are accurate)
         │
         ▼
User receives response + citations
```

**Key Design Decisions:**

1. **Re-embed queries:** Queries use the same embedding model as document chunks for consistency
2. **Top-K retrieval:** Return top 5-10 chunks to balance context size and relevance
3. **Chunk overlap:** Ensures no important context is split across boundaries
4. **Citation validation:** Prevents the LLM from citing information not in the retrieved context

### 3. Chat Conversation Flow

```
User sends message
         │
         ├─→ Extract intent (search, chat, document reference?)
         │
         ├─→ If SEARCH intent:
         │   └─→ Retrieve relevant chunks
         │
         ├─→ Augment context with history + retrieved chunks
         │
         └─→ Send to LLM with reasoning prompt
             │
             ▼
         LLM generates response
             │
             ├─→ Extract citations
             │
             ├─→ Validate against retrieved chunks
             │
             └─→ Stream response to user
```

## Technology Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **Frontend** | React | 19 | UI framework |
| | TypeScript | ~5.9 | Type safety |
| | Vite | 8 | Build tool |
| | react-router-dom | 7.13 | Client-side routing |
| **Backend** | FastAPI | (latest) | HTTP API framework |
| | Python | 3.13 | Application language |
| | Uvicorn | (latest) | ASGI server |
| **Vector DB** | Qdrant | 1.13.2 | Vector storage |
| **LLM** | OpenAI API | (latest) | Chat & embeddings |
| **Embeddings** | text-embedding-3-small | (latest) | Vector generation |
| **Data** | SQLite | 3 | Feedback storage |
| **Ingestion** | PyPDF2, python-docx, etc. | (latest) | Document parsing |

## Configuration Management

All sensitive and deployment-specific settings are managed via environment variables (`.env` file).

**Key Variables:**
```
OPENAI_API_KEY              # API key for OpenAI
OPENAI_CHAT_MODEL           # Default: gpt-4o
OPENAI_EMBEDDING_MODEL      # Default: text-embedding-3-small
QDRANT_URL                  # Default: http://localhost:6333
QDRANT_COLLECTION           # Collection name in Qdrant
CHUNK_SIZE                  # Default: 1000 tokens
CHUNK_OVERLAP               # Default: 200 tokens
TOP_K                       # Default: 5 chunks to retrieve
```

## Key Design Decisions

### 1. Separating Ingestion from Retrieval

Ingestion is a **batch process** (expensive, asynchronous):
- User uploads documents
- System processes in background
- Vectors are pre-computed and stored

Retrieval is a **real-time process** (fast):
- User asks a question
- System searches pre-computed vectors
- Returns results in <1 second

### 2. Using Embeddings for Semantic Search

Why not keyword search?
- **Semantic:** Finds similar *meaning*, not just matching words
- **Language-agnostic:** Works across terminology variations
- **Example:** "What is AnaCredit?" matches: "Regulatory reporting framework", "CREDIT Directive"

### 3. Citation Tracking

Why validate citations?
- **Prevents hallucination:** LLM can't cite things not in context
- **Trust:** Users can verify answers against source documents
- **Compliance:** BIL needs auditable, traceable decisions

### 4. Conversation History

Why keep chat history?
- **Context awareness:** Follow-up questions make sense
- **Reasoning:** LLM understands conversation flow
- **User experience:** Natural dialogue instead of isolated questions

## Scalability & Performance

### Current Setup (Development)
- **Single backend instance** (uvicorn)
- **Single Qdrant instance** (in-memory cache + disk persistence)
- **Synchronous ingestion** (one document at a time)

### Production Considerations (for OpenShift deployment)
- **Horizontal scaling:** Multiple backend replicas behind a load balancer
- **Qdrant clustering:** Multiple nodes for fault tolerance
- **Async ingestion:** Queue system for document processing
- **Caching:** Redis for chat history and frequent queries
- **Monitoring:** Prometheus metrics for latency, error rates, vector search performance

## Data Flow Example: Complete User Journey

```
1. User: "Upload AnaCredit regulation document"
   → Frontend sends PDF to backend
   → Backend chunks + embeds document
   → Vectors stored in Qdrant
   → Metadata indexed in SQLite

2. User: "What is the scope of AnaCredit?"
   → Frontend sends query to backend
   → Backend embeds query with same model
   → Qdrant searches for 5 most similar chunks
   → Backend formats chunks into context
   → Backend sends to gpt-4o: "Using this context: [...], answer: What is scope?"
   → gpt-4o: "AnaCredit is a regulation requiring... [cites chunks]"
   → Backend validates citations
   → Frontend displays:"AnaCredit is... (Sources: Regulation PDF, Chapter 2)"

3. User: "How does this relate to Basel III?"
   → Backend includes chat history in context
   → Retrieves new chunks about Basel III
   → gpt-4o reasons over both AnaCredit + Basel III information
   → Generates cross-document answer
   → Citations point to multiple sources
```

## API endpoints

### Chat
- `POST /chat` — Send a message, get a response with citations

### Ingestion
- `POST /ingest/upload` — Upload a document
- `POST /ingest/reindex` — Reindex all documents
- `GET /ingest/reindex/stream` — Stream reindexing progress

### Health & Info
- `GET /health` — System health check
- `GET /docs` — API documentation (Swagger UI)

## Summary

AnaGuide is a production-grade RAG application that:

1. **Ingests** business documents into a searchable vector database
2. **Retrieves** relevant context for user questions
3. **Augments** LLM prompts with retrieved context
4. **Generates** accurate, cited answers grounded in documents
5. **Validates** citations to prevent hallucination
6. **Tracks** user feedback for continuous improvement

The architecture separates concerns (frontend, backend, vector DB, LLM) for independent scaling and deployment on containerized platforms like OpenShift.
