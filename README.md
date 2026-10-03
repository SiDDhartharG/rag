# Ask your documents (RAG from scratch)

Put documents in, ask questions, get answers with the sources they came from. Built step by step in Python to learn how RAG works: no LangChain, every stage is a small readable file.

```
your files → cut into chunks → turned into vectors → stored
your question → find the closest chunks → send them to an AI model → answer + sources
```

Everything runs on your own machine. The default AI model is local (Ollama), so it is free and nothing leaves your computer.

---

## 1. One-time setup

You need a Mac with [Homebrew](https://brew.sh). Run these from the project folder.

```bash
brew install uv ollama          # tools: Python manager and local AI
node --version                  # needs Node.js 20 or newer; if missing, run: brew install node
uv sync                         # installs the Python packages (about 1 minute)
cd frontend && npm install && cd ..   # installs the web page packages
ollama pull llama3.2            # downloads the AI model (about 2 GB, once)
```

That is all. You never need to "activate" anything; `uv run` handles the Python environment.

---

## 2. Start it (every time)

Open **three terminal tabs** in the project folder and run one command in each:

**Tab 1: the AI model**
```bash
ollama serve
```

**Tab 2: the backend**
```bash
uv run uvicorn backend.app.main:create_app --factory --reload
```

**Tab 3: the web page**
```bash
cd frontend && npm run dev
```

Then open **http://localhost:5180** in your browser. To stop anything, press `Ctrl+C` in its tab.

> If `ollama serve` says the address is already in use, Ollama is already running. That is fine, skip tab 1.

---

## 3. Simple walkthrough

**Step 1: add a document.**
Open **http://localhost:5180/config** (the *Settings* link at the top). Click **Add documents** and pick a PDF, `.txt` or `.md` file. The status goes *Waiting → Indexing → Ready*. That means it has been cut up and stored.

**Step 2: ask a question.**
Click **Ask** at the top (**http://localhost:5180**). Type a question about your document and press **Enter**. The answer streams in, and below it you see the **sources**: the pieces of your document the answer is based on, each with a score (higher means a closer match).

**Step 3: look inside (the fun part).**
Tick **Show prompt** and ask again. Open "Prompt sent to the model" to see exactly what the AI was given. Tick **Retrieval only** to see what the search finds without calling the AI at all.

**Step 4: tune it.**
Back in **Settings** you can change:
- **Chunking**: how documents are cut up (strategy, chunk size, overlap). The coloured ruler shows what a change does. After changing these, click the **Re-index** button that appears.
- **Retrieval**: how many chunks go to the AI, and the minimum score a chunk needs.
- **Model**: Ollama, Claude, or Echo (no AI, for testing), plus the instructions given to the model.

Ask the same question again after each change and compare the answers. That is how you learn what each setting does.

Notes: the chat is not saved (refresh clears it), and every question is answered on its own, so follow-up questions like "and what about him?" will not work.

---

## 4. All commands

### Run the app
| What | Command |
|---|---|
| Start the AI model | `ollama serve` |
| Start the backend (http://127.0.0.1:8000) | `uv run uvicorn backend.app.main:create_app --factory --reload` |
| Start the web page (http://localhost:5180) | `cd frontend && npm run dev` |
| API test page (try endpoints in the browser) | open http://127.0.0.1:8000/docs |

### Use it from the terminal (no web page needed)
Put files in the `data/` folder first.

| What | Command |
|---|---|
| Index everything in `data/` | `uv run python -m rag.cli ingest` |
| Index one file | `uv run python -m rag.cli ingest data/notes.pdf` |
| Ask a question | `uv run python -m rag.cli ask "Where did he study?"` |
| Show the prompt the AI received | `uv run python -m rag.cli ask "Where did he study?" --show-prompt` |
| Search only, no AI | `uv run python -m rag.cli ask "Where did he study?" --retrieval-only` |
| Use Claude for one question | `uv run python -m rag.cli ask "Where did he study?" --provider claude` |
| Test without any AI model | `uv run python -m rag.cli ask "Where did he study?" --provider echo` |

### Models
| What | Command |
|---|---|
| List downloaded models | `ollama list` |
| Download another model | `ollama pull <name>` (then set the name in Settings) |
| Stop the AI model | `pkill ollama` |

### Learn by running experiments
Each script prints what happens at one step. Run any of them with `uv run python experiments/<file>`:

| File | Shows |
|---|---|
| `01_tokens.py` | How text is split into tokens |
| `02_chunking.py` | All five ways of cutting a document, side by side |
| `03_embeddings.py` | How "similar meaning" becomes a number |
| `06_score_walkthrough.py` | How one match score is calculated, step by step |
| `07_store.py` | The vector database (run it twice) |
| `08_pipeline.py` | Re-indexing behaviour |
| `10_llm_config.py` | Switching AI models from config |

(The others, `00`, `04`, `05`, `08_filter`, `09`, are smaller demos. See [docs/details.md](docs/details.md) for the full list.)

### Check that everything works
| What | Command |
|---|---|
| Backend tests | `uv run pytest tests -q` |
| Web page type-check and build | `cd frontend && npm run build` |

---

## 5. Using Claude instead of Ollama (optional)

1. Get an API key from Anthropic.
2. Put it in the `.env` file in the project folder: `ANTHROPIC_API_KEY=your-key-here`
3. Restart the backend (tab 2).
4. In **Settings → Model**, choose **Claude**, and click **Save changes**.

The key stays on your computer in `.env`. The web page never sees it, and `.env` is not uploaded to git.

---

## 6. If something goes wrong

| What you see | What to do |
|---|---|
| Web page says **"The API is not running"** | Start the backend (tab 2). The page reconnects by itself. |
| Answer says **"Cannot reach Ollama"** | Start `ollama serve` (tab 1). |
| Answer says **"model 'llama3.2' not found"** | Run `ollama pull llama3.2`. |
| Answer says **"I don't know: nothing in the indexed documents…"** | No chunk matched well enough. Lower **Minimum match score** in Settings, rephrase the question, or check a document is *Ready*. |
| **"No Anthropic credentials"** | Add `ANTHROPIC_API_KEY` to `.env` (section 5), or switch back to Ollama. |
| `npm run dev` says **port 5180 is in use** | Another copy is running. Stop it, or change the port in `frontend/vite.config.ts` (and add it to the allowed list in `backend/app/main.py`). |
| Answers are wrong or incomplete | Usually the small local model. Try a larger Ollama model, or Claude. Use **Show prompt** to check the right text reached it. |
| Changed chunk settings but answers did not change | Click **Re-index** on the Settings page. |

---

## Where things are

| Folder / file | What it is |
|---|---|
| `rag/` | The RAG code (load, chunk, embed, store, search, answer). **This is the learning part.** |
| `backend/` | The API the web page talks to |
| `frontend/` | The web page (Ask and Settings) |
| `config.toml` | Default settings, copied into the database the first time the backend starts |
| `data/` | Your documents and the stored vectors (not uploaded to git) |
| `experiments/` | Small scripts that print what each step does |
| `tests/` | Backend tests |
| `docs/details.md` | The long technical reference |
| `ROADMAP.md` | The original plan |

Want the deeper explanations (how each chunking strategy behaves, what the scores mean, what I learned along the way)? Read [docs/details.md](docs/details.md).
