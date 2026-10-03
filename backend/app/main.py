"""FastAPI backend: stores settings in SQLite and exposes the rag/ package over HTTP.

Run from the project root (so config.toml and data/ resolve):
    uv run uvicorn backend.app.main:create_app --factory --reload
Then open http://127.0.0.1:8000/docs for interactive API docs.
"""

import json
from collections.abc import Iterator
from dataclasses import asdict
from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from backend.app.db import Document, Settings, make_engine
from backend.app.schemas import (
    DocumentOut,
    LLMSettings,
    QueryRequest,
    RagConfigResponse,
    RagSettings,
    to_rag_config,
)
from rag.config import RagConfig, load_config
from rag.generation import NO_ANSWER, build_prompt, retrieve
from rag.llm import get_llm
from rag.pipeline import ingest
from rag.store import get_collection

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
# Settings that change the stored vectors. Editing one of these makes existing documents stale.
INDEX_FIELDS = {"strategy", "chunk_tokens", "overlap"}


def sse(event: str, data) -> str:
    """Format one Server-Sent Event. The browser's EventSource / fetch reader splits on blank lines."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def create_app(
    engine: Engine | None = None,
    collection: str = "docs",
    upload_dir: Path = Path("data/uploads"),
) -> FastAPI:
    """App factory: tests pass their own engine/collection/upload_dir so they never touch real data."""
    engine = engine or make_engine()
    upload_dir.mkdir(parents=True, exist_ok=True)

    app = FastAPI(title="RAG API")
    app.add_middleware(
        CORSMiddleware,
        # The React dev server. 5180 is this project's own port (see frontend/vite.config.ts); 5173 is Vite's default.
        allow_origins=[f"http://{host}:{port}" for host in ("localhost", "127.0.0.1") for port in (5173, 5180)],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---- helpers -------------------------------------------------------------------------------

    def get_session() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    def settings_row(session: Session) -> Settings:
        """Return the settings row, creating it from config.toml the first time."""
        row = session.get(Settings, 1)
        if row is None:
            c = load_config()
            rag = RagSettings(
                strategy=c.ingest.strategy,
                chunk_tokens=c.ingest.chunk_tokens,
                overlap=c.ingest.overlap,
                top_k=c.retrieval.top_k,
                min_score=c.retrieval.min_score,
            )
            llm = LLMSettings(
                provider=c.llm.provider,
                system_prompt=c.llm.system_prompt,
                claude=asdict(c.llm.claude),
                ollama=asdict(c.llm.ollama),
            )
            row = Settings(id=1, rag_json=rag.model_dump_json(), llm_json=llm.model_dump_json())
            session.add(row)
            session.commit()
            session.refresh(row)
        return row

    def current_config(session: Session) -> RagConfig:
        row = settings_row(session)
        return to_rag_config(
            RagSettings.model_validate_json(row.rag_json),
            LLMSettings.model_validate_json(row.llm_json),
            collection,
        )

    def run_ingest(doc_ids: list[int]) -> None:
        """Background job: index documents one by one, recording status so the UI can poll it."""
        for doc_id in doc_ids:
            with Session(engine) as session:
                doc = session.get(Document, doc_id)
                if doc is None:  # deleted while queued
                    continue
                doc.status, doc.error = "indexing", None
                session.commit()
                try:
                    stats = ingest(upload_dir / doc.filename, current_config(session).ingest)
                    doc.status, doc.chunks = "ready", stats["chunks"]
                except Exception as e:  # report any failure on the document instead of crashing the worker
                    doc.status, doc.error = "failed", str(e)
                session.commit()

    # ---- health --------------------------------------------------------------------------------

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    # ---- config --------------------------------------------------------------------------------

    @app.get("/config/rag", response_model=RagConfigResponse)
    def get_rag_config(session: Session = Depends(get_session)):
        row = settings_row(session)
        return RagConfigResponse(
            settings=RagSettings.model_validate_json(row.rag_json), needs_reindex=row.needs_reindex
        )

    @app.put("/config/rag", response_model=RagConfigResponse)
    def put_rag_config(new: RagSettings, session: Session = Depends(get_session)):
        row = settings_row(session)
        old = RagSettings.model_validate_json(row.rag_json)
        changed_index = any(getattr(old, f) != getattr(new, f) for f in INDEX_FIELDS)
        has_docs = session.exec(select(Document)).first() is not None
        row.rag_json = new.model_dump_json()
        row.needs_reindex = row.needs_reindex or (changed_index and has_docs)
        session.add(row)
        session.commit()
        return RagConfigResponse(settings=new, needs_reindex=row.needs_reindex)

    @app.get("/config/llm", response_model=LLMSettings)
    def get_llm_config(session: Session = Depends(get_session)):
        return LLMSettings.model_validate_json(settings_row(session).llm_json)

    @app.put("/config/llm", response_model=LLMSettings)
    def put_llm_config(new: LLMSettings, session: Session = Depends(get_session)):
        row = settings_row(session)
        row.llm_json = new.model_dump_json()
        session.add(row)
        session.commit()
        return new

    # ---- documents -----------------------------------------------------------------------------

    @app.get("/documents", response_model=list[DocumentOut])
    def list_documents(session: Session = Depends(get_session)):
        return session.exec(select(Document).order_by(Document.id)).all()

    @app.post("/documents", response_model=DocumentOut, status_code=202)
    async def upload_document(file: UploadFile, background: BackgroundTasks, session: Session = Depends(get_session)):
        # Path(...).name strips any directory parts, so "../../etc/x.txt" cannot escape upload_dir.
        name = Path(file.filename or "").name
        if not name or name.startswith(".") or Path(name).suffix.lower() not in ALLOWED_EXTENSIONS:
            raise HTTPException(400, f"Unsupported file. Allowed types: {sorted(ALLOWED_EXTENSIONS)}")
        data = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, f"File too large (limit {MAX_UPLOAD_BYTES // (1024 * 1024)} MB)")

        (upload_dir / name).write_bytes(data)
        doc = session.exec(select(Document).where(Document.filename == name)).first()
        if doc is None:
            doc = Document(filename=name)
        doc.status, doc.error = "pending", None  # re-uploading the same name re-indexes it
        session.add(doc)
        session.commit()
        session.refresh(doc)
        background.add_task(run_ingest, [doc.id])  # indexing takes seconds; do it after responding
        return doc

    @app.delete("/documents/{doc_id}", status_code=204)
    def delete_document(doc_id: int, session: Session = Depends(get_session)):
        doc = session.get(Document, doc_id)
        if doc is None:
            raise HTTPException(404, "No such document")
        if doc.status == "indexing":
            raise HTTPException(409, "Document is being indexed; try again in a moment")
        get_collection(collection).delete(where={"source": doc.filename})  # remove its vectors
        (upload_dir / doc.filename).unlink(missing_ok=True)
        session.delete(doc)
        session.commit()

    @app.post("/reindex", status_code=202)
    def reindex(background: BackgroundTasks, session: Session = Depends(get_session)) -> dict:
        """Re-ingest every document with the current settings (after changing strategy/chunk size)."""
        docs = session.exec(select(Document)).all()
        for d in docs:
            d.status = "pending"
            session.add(d)
        row = settings_row(session)
        row.needs_reindex = False
        session.add(row)
        session.commit()
        background.add_task(run_ingest, [d.id for d in docs])
        return {"queued": len(docs)}

    # ---- query (streaming) ---------------------------------------------------------------------

    @app.post("/query")
    def query(req: QueryRequest, session: Session = Depends(get_session)):
        """Streams Server-Sent Events: `sources`, then `token`s (or `error`), then `done`."""
        cfg = current_config(session)
        hits = retrieve(req.question, cfg)
        sources = [
            {"score": round(h["score"], 4), "source": h["metadata"]["source"],
             "chunk_index": h["metadata"]["chunk_index"], "text": h["text"]}
            for h in hits
        ]

        def events() -> Iterator[str]:
            yield sse("sources", sources)
            if not hits:  # nothing relevant: skip the LLM, same rule as the CLI
                yield sse("token", NO_ANSWER)
            else:
                system, user = build_prompt(req.question, hits, cfg.llm.system_prompt)
                if req.debug:  # also in retrieval-only mode: shows what WOULD be sent
                    yield sse("prompt", {"system": system, "user": user})
                if not req.retrieval_only:
                    try:
                        for piece in get_llm(cfg.llm).stream(system, user):
                            yield sse("token", piece)
                    except RuntimeError as e:  # e.g. Ollama not running, bad API key
                        yield sse("error", str(e))
            yield sse("done", {})

        return StreamingResponse(events(), media_type="text/event-stream")

    return app
