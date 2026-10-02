# RAG Learning Project — Roadmap

**Goal:** understand how RAG works by building it. The learning is in the Python RAG core (ingest + retrieve/generate). The React UI and backend are supporting cast — keep them thin.

## Architecture

```
┌──────────────────┐        ┌───────────────────────────────┐
│ React UI         │  HTTP  │ Backend (FastAPI + SQLite)    │
│  • Config page   │ ─────► │  • stores config (models,     │
│  • Chat/query    │        │    chunk size, top-k, ...)    │
└──────────────────┘        │  • REST API                   │
                            │         │ imports             │
                            │         ▼                     │
                            │ rag/ (pure Python package)    │
                            │  ingest:   load→chunk→embed→store │
                            │  query:    embed→retrieve→prompt→LLM │
                            └─────────┬─────────────────────┘
                                      ▼
                               Vector DB (Chroma, local)
```

Key decision: **`rag/` is a plain Python package with no web code**. It's testable from a script/notebook first; FastAPI just calls it. This keeps your learning code clean.

## Stack (defaults — change freely)

| Layer | Choice | Why |
|---|---|---|
| Python env | `uv` + Python 3.12 | Fast, one tool for venv + deps. (3.13 is installed, but ML wheels lag; pin 3.12.) |
| Tokenizer | `tiktoken` | See real token counts for chunking |
| Embeddings | `sentence-transformers` (`all-MiniLM-L6-v2`), local | Free, offline, see the vectors yourself |
| Vector DB | Chroma (persistent, local) | Zero infra. Later swap to Qdrant/pgvector to learn the difference |
| LLM | Claude API (or Ollama for local) | Behind a small interface so it's swappable |
| Backend | FastAPI + SQLite (SQLModel) | Minimal, auto docs at `/docs` |
| Frontend | Vite + React + TypeScript | Node 22 already installed |

## Repo layout

```
rag/
├── ROADMAP.md
├── backend/           # FastAPI app + config storage
│   └── app/
├── rag/               # ← the learning core (Python package)
│   ├── loaders.py
│   ├── chunking.py
│   ├── embeddings.py
│   ├── store.py
│   ├── retrieval.py
│   ├── generation.py
│   └── pipeline.py
├── experiments/       # notebooks/scripts for poking at things
├── data/              # sample docs (+ chroma persistence, gitignored)
├── frontend/          # Vite React app
└── pyproject.toml
```

---

## Phase 0 — Python setup (≈ 30 min)

- [ ] Install uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- [ ] `uv init` in the project root, pin Python 3.12 (`uv python pin 3.12`)
- [ ] `uv add tiktoken sentence-transformers chromadb fastapi "uvicorn[standard]" sqlmodel pydantic-settings python-dotenv anthropic`
- [ ] `uv add --dev pytest ruff jupyter`
- [ ] `.env` for `ANTHROPIC_API_KEY`; `.gitignore` for `.env`, `data/chroma/`, `.venv/`
- [ ] `git init`
- [ ] Sanity script: embed one sentence, print the vector shape (should be 384)

**Done when:** `uv run python experiments/00_hello_embed.py` prints a vector.

## Phase 1 — RAG Part 1: Ingestion (the core learning) 

Build in this order. Each step has an experiment that makes the concept concrete.

1. **Load** — read `.txt` / `.md` / `.pdf` into `Document(text, metadata)`.
2. **Tokenize** — use `tiktoken` to count tokens. *Experiment:* why does 1000 characters ≠ 1000 tokens?
3. **Chunk** — implement three strategies and compare:
   - fixed-size with overlap
   - recursive (split on paragraph → sentence → word)
   - (stretch) markdown-header / semantic chunking
   *Experiment:* chunk the same doc 3 ways, eyeball where sentences get cut in half.
4. **Embed** — batch chunks through sentence-transformers. *Experiment:* cosine similarity between related/unrelated sentences by hand with numpy; plot with PCA/UMAP.
5. **Store** — write `(id, vector, text, metadata)` to Chroma. Make ingestion idempotent (stable chunk IDs from content hash, so re-ingesting doesn't duplicate).
6. **Pipeline** — `ingest(path, config) -> stats` tying it together.

**Done when:** you can ingest a folder of docs and inspect the collection (count, sample chunks, metadata).

**Concepts you'll own after this:** tokens vs characters, chunk size/overlap trade-offs, what an embedding actually is, why the same model must embed docs and queries, what a vector DB stores.

## Phase 2 — RAG Part 2: Retrieval + Generation (the other half of the core)

1. **Retrieve** — embed the query, top-k similarity search. *Experiment:* print scores; try queries that should/shouldn't match; see what a bad chunk size does to results.
2. **Build the prompt** — system prompt + retrieved context + question. Number the chunks so the model can cite `[1]`, `[2]`.
3. **Generate** — call the LLM behind a `LLMClient` interface (Claude impl first; Ollama impl optional). Support streaming.
4. **Return sources** — answer + the chunks used (text, doc, score).
5. **Failure modes** — handle "no relevant context": similarity threshold → "I don't know" instead of hallucinating.
6. **Evaluate (lightweight)** — 10–20 hand-written Q&A pairs over your sample docs; measure retrieval hit-rate (is the right chunk in top-k?). Use this to tune chunk size / k.
7. **Upgrades (stretch, pick any):** hybrid search (BM25 + vector), reranking with a cross-encoder, metadata filtering, query rewriting, MMR for diversity.

**Done when:** `uv run python -m rag.cli ask "question"` gives a grounded, cited answer, and your eval set gives you a number you can improve.

## Phase 3 — Backend (config + API)

Built *after* the core works, so the API shapes follow real needs.

- [ ] SQLite tables: `RagConfig` (embedding model, chunk size/overlap, chunking strategy, top-k, threshold), `LLMConfig` (provider, model, temperature, system prompt), `Document` (ingestion status)
- [ ] Endpoints:
  - `GET/PUT /config/rag`, `GET/PUT /config/llm`
  - `POST /documents` (upload + trigger ingest), `GET /documents`, `DELETE /documents/{id}`
  - `POST /query` (SSE streaming) → `{answer, sources[]}`
- [ ] API keys stay in `.env`/server side — never stored in the frontend
- [ ] Gotcha to handle: changing the embedding model or chunking config means **re-ingesting** (vectors from different models aren't comparable). Surface this as a "needs re-index" flag.
- [ ] CORS for the Vite dev server; a few pytest API tests

**Done when:** everything in Phases 1–2 is drivable via `/docs` (Swagger) with no UI.

## Phase 4 — React UI Part 1: Configuration

- [ ] `npm create vite@latest frontend -- --template react-ts`
- [ ] Config form: embedding model, chunking strategy, chunk size, overlap, top-k, LLM provider/model, temperature, system prompt
- [ ] Document upload + ingestion status list
- [ ] "Needs re-index" banner + Re-index button
- [ ] Keep state simple: TanStack Query for server state, plain `useState` for forms

## Phase 5 — React UI Part 2: Query

- [ ] Chat-style input + streamed answer
- [ ] Sources panel: each retrieved chunk with score + document name; highlight the `[n]` citations
- [ ] "Debug view" toggle showing the exact prompt sent to the LLM — **this is the most educational feature in the whole UI**
- [ ] Show retrieval-only mode (no LLM) to see search quality in isolation

## Phase 6 — Stretch / Next Learning

- **Rebuild with a framework (LangChain or LlamaIndex):** reimplement the same pipeline (load → chunk → embed → store → retrieve → generate) using the framework, against the same sample docs and eval set. Compare code size, retrieval results, and what's hidden from you (default chunkers, prompts, retry logic). Decide whether it's worth using in real projects. Intentionally left out of Phases 1–2 so you learn the raw steps first.
- Swap `tiktoken` for the embedding model's own tokenizer (from `sentence-transformers`) for exact token counts
- Swap Chroma → Qdrant or pgvector and compare
- Compare embedding models (MiniLM vs bge vs OpenAI/Voyage) using your eval set
- Conversation memory / follow-up question rewriting
- Agentic RAG (LLM decides when/what to retrieve — tool use)
- Observability: log every query's chunks, prompt, latency, tokens

---

## Suggested order & time

| Phase | Effort | Notes |
|---|---|---|
| 0 Setup | 0.5 hr | |
| 1 Ingestion | 1–2 days | Spend the time on experiments, not speed |
| 2 Retrieval+LLM | 1–2 days | Eval set is the payoff |
| 3 Backend | 0.5–1 day | |
| 4–5 UI | 1–2 days | |

Build 1 → 2 first, **entirely without UI or backend**, as scripts. That's where the learning is; the rest is plumbing you can build quickly once the core is solid.

## Open decisions (revisit as you go)

- LLM: Claude API vs local Ollama? (Interface supports both)
- Sample corpus: pick something you know well (your own notes, a book, docs for a tool you use) so you can judge answer quality
- Single collection vs one per config (affects re-index flow)
