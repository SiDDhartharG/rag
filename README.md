# RAG from scratch

A personal project to understand how Retrieval-Augmented Generation works by building each step by hand in Python. No LangChain: every stage (load, chunk, embed, store, retrieve, prompt, generate) is a small readable file.

See [ROADMAP.md](ROADMAP.md) for the full plan. Status: the Python RAG core and the FastAPI backend work. The React UI is not built yet.

## How it works

```
INGEST   file ──► load ──► chunk ──► embed ──► store in Chroma
ASK      question ──► embed ──► search Chroma ──► drop weak chunks ──► build prompt ──► LLM ──► answer + sources
```

| Step | File | What it does |
|---|---|---|
| Load | `rag/loaders.py` | Reads `.pdf`, `.txt`, `.md` into `Document(text, metadata)` |
| Chunk | `rag/chunking.py` | Five strategies: `fixed`, `recursive`, `sentence`, `structure`, `semantic` |
| Embed | `rag/embeddings.py` | `all-MiniLM-L6-v2` (local, 384 numbers per text, unit length so dot product = cosine similarity) |
| Store | `rag/store.py` | Persistent Chroma DB in `data/chroma/`; chunk IDs are content hashes, so re-ingesting never duplicates |
| Ingest | `rag/pipeline.py` | `ingest(path, config)` ties the steps together; removes stale chunks when a file changes |
| Retrieve | `rag/retrieval.py` | Top-k similarity search, drops chunks below `min_score` |
| Prompt + answer | `rag/generation.py` | Numbers the chunks `[1] [2]...`, calls the LLM, returns answer + sources |
| LLM providers | `rag/llm.py` | `ollama` (local), `claude` (Anthropic API), `echo` (offline test, no model) |
| Settings | `rag/config.py`, `config.toml` | Everything tunable lives in `config.toml` |
| CLI | `rag/cli.py` | `ingest` and `ask` commands, with `[step]` progress prints |

## Setup

Requirements: macOS/Linux, [uv](https://docs.astral.sh/uv/), and [Ollama](https://ollama.com) for the default local model.

```bash
brew install uv ollama
uv sync                       # creates .venv with Python 3.12 and installs dependencies
cp .env.example .env          # only needed if you want to use Claude
ollama serve                  # leave running in its own terminal tab
ollama pull llama3.2          # about 2 GB download
```

Put documents (PDF, txt, md) in `data/`. The folder's contents are gitignored, so personal files such as a resume are not committed.

## Usage

Run these from the project folder. `uv run` uses the project's environment, so there is nothing to activate.

```bash
# 1. Index your documents (safe to re-run)
uv run python -m rag.cli ingest

# 2. Ask a question (uses the provider set in config.toml, Ollama by default)
uv run python -m rag.cli ask "What programming languages and tools does he know?"

# See the exact prompt the model received
uv run python -m rag.cli ask "Where did he study?" --show-prompt

# Retrieval only, no LLM: shows which chunks match and their scores
uv run python -m rag.cli ask "What did he build at BrowserStack?" --retrieval-only

# Switch provider for one question
uv run python -m rag.cli ask "Where did he study?" --provider claude   # needs ANTHROPIC_API_KEY in .env
uv run python -m rag.cli ask "Where did he study?" --provider echo     # no model, just tests the wiring
```

Questions that match nothing well enough (for example "How do I bake sourdough bread?") get an "I don't know" without calling the LLM at all.

## Backend API

A FastAPI app (`backend/app/`) stores settings in SQLite (`data/app.db`) and exposes the RAG core over HTTP, so the React UI can configure and query it. Settings are seeded from `config.toml` the first time, then live in the database.

```bash
uv run uvicorn backend.app.main:create_app --factory --reload   # run from the project root
```

Open http://127.0.0.1:8000/docs for interactive docs.

| Endpoint | Purpose |
|---|---|
| `GET/PUT /config/rag` | Chunking strategy, chunk size, overlap, top_k, min_score. Returns `needs_reindex` when a change affects stored vectors |
| `GET/PUT /config/llm` | Provider (`ollama`/`claude`/`echo`), model settings, system prompt |
| `POST /documents` | Upload a pdf/txt/md (max 20 MB); indexed in the background |
| `GET /documents` | List documents with status `pending`, `indexing`, `ready` or `failed` |
| `DELETE /documents/{id}` | Remove the document and its vectors |
| `POST /reindex` | Re-ingest all documents with the current settings |
| `POST /query` | Streams Server-Sent Events: `sources`, then `token`s (or `error`), then `done`. Flags: `retrieval_only`, `debug` (also streams the exact prompt) |

```bash
curl -N -X POST localhost:8000/query -H 'content-type: application/json' \
  -d '{"question": "Where did he study?"}'
```

Notes: API keys are never accepted or returned by the API; they stay in `.env` on the server. CORS allows only the Vite dev server (`localhost:5173`). The API has no authentication, so run it locally only. Documents indexed with the CLI are searched too, but only uploaded ones appear in `GET /documents`.

Run the tests (they use an in-memory DB, a temp folder and a throwaway Chroma collection, and no real LLM):

```bash
uv run pytest tests -q
```

## Configuration

Edit `config.toml`; no code changes needed. (The backend reads it only to seed its first settings.)

| Setting | Meaning |
|---|---|
| `ingest.strategy` | `fixed`, `recursive`, `sentence`, `structure`, `semantic` |
| `ingest.chunk_tokens` / `overlap` | Chunk size in tokens; overlap is used only by `fixed` |
| `retrieval.top_k` | How many chunks are sent to the LLM |
| `retrieval.min_score` | Chunks scoring below this are dropped. 0.15 works for the resume demo: answerable questions scored 0.22 or higher, off-topic ones 0.09 or lower |
| `llm.provider` | `ollama`, `claude` or `echo` |
| `llm.claude.model` / `effort` | Claude model and effort level. Set `effort = ""` for models that reject it, such as Haiku 4.5 |
| `llm.ollama.model` / `host` | Ollama model and server address |

After changing any `ingest.*` setting, run `ingest` again. Changing the embedding model would need a full re-index, because vectors from different models can't be compared (not yet automated).

## Experiments

Each concept has a script in `experiments/` that prints intermediate values. Run one with `uv run python experiments/NN_name.py`.

| Script | Shows |
|---|---|
| `01_tokens.py` | Characters vs tokens, how words split into tokens |
| `02_chunking.py` | All five chunking strategies side by side on one document |
| `03_embeddings.py` | Cosine similarity by hand; which chunk each strategy retrieves |
| `04_meaning.py` | Embeddings capture meaning from context, not a dictionary |
| `05_model_peek.py` | Inside the embedding model: size, 256-token input limit, tokenizer |
| `06_score_walkthrough.py` | How a similarity score is computed, step by step |
| `07_store.py` | Chroma persistence and stable IDs (run it twice) |
| `08_pipeline.py` | `ingest()` behaviour: unchanged, stale cleanup, chunk-size effects |
| `08_filter.py` | Metadata filtering with `where` |
| `09_retrieve_prompt.py` | Score thresholds, filters, and the exact prompt sent to the LLM |
| `10_llm_config.py` | Provider switching from config, and the failure messages |

## What I learned / things to know

- **Chunking decides what retrieval can find.** On the sample resume, `structure` chunking (split at headings) found the right chunk for all 3 test questions. `sentence` found none, and `semantic` made many tiny, context-free chunks. This is one short document and three questions, so treat it as an illustration, not a benchmark.
- **A high score is not a correct answer.** A 5-token chunk ("Engineering Intern") outscored the real education chunk. Compare scores relative to each other, and use top-k rather than trusting the top result alone.
- **Embeddings capture topic, not logic.** "I do not love cooking pasta" scored higher against "I love cooking pasta" than a true paraphrase did.
- **The embedding model truncates input at 256 tokens.** Chunks are counted with `tiktoken`, which differs slightly from the model's own tokenizer, so keep chunks well under 256.
- **Small local models are inconsistent.** `llama3.2` (3B) answered correctly but sometimes omitted items, ignored the "cite [1]" instruction, and changed its wording between runs on the same question. Retrieval is the same each time; the variation comes from the model. Try a larger model or Claude for steadier answers.
- **Retrieved text goes into the prompt as-is.** A document containing instructions could try to steer the model (prompt injection). Fine for your own files; be careful with documents you do not control.

## Not done yet

- Eval set (hand-written questions with known right chunks) to measure retrieval instead of eyeballing it
- Inline citations from small models, reranking, hybrid search
- React UI (Phases 4 and 5 in the roadmap)
- Automatic re-index when the embedding model changes
