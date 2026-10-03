"""API tests. Each test gets a fresh in-memory DB, a temp upload folder and its own Chroma collection,
so nothing touches your real data. They use the 'echo' LLM provider, so no model is called."""

import json

import chromadb
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, create_engine

import backend.app.main as main
from backend.app.main import create_app
from rag.store import CHROMA_PATH

COLLECTION = "test_api"
FRANCE = b"# France\nThe capital of France is Paris. The Eiffel Tower is a famous landmark in Paris.\n"


@pytest.fixture
def client(tmp_path):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool  # in-memory, shared
    )
    SQLModel.metadata.create_all(engine)
    app = create_app(engine, collection=COLLECTION, upload_dir=tmp_path / "uploads")
    with TestClient(app) as c:
        c.put("/config/llm", json={**c.get("/config/llm").json(), "provider": "echo"})
        yield c
    try:
        chromadb.PersistentClient(path=str(CHROMA_PATH)).delete_collection(COLLECTION)
    except Exception:
        pass


def events(resp) -> list[tuple[str, object]]:
    """Parse a Server-Sent Events body into [(event_name, data), ...]."""
    out = []
    for block in resp.text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines())
        out.append((lines["event"], json.loads(lines["data"])))
    return out


def upload(client, name="france.md", data=FRANCE):
    return client.post("/documents", files={"file": (name, data)})


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_config_defaults_come_from_config_toml(client):
    body = client.get("/config/rag").json()
    assert body["settings"]["strategy"] == "structure"
    assert body["needs_reindex"] is False


@pytest.mark.parametrize("bad", [
    {"chunk_tokens": 5000},                 # over the embedding model's 256-token limit
    {"chunk_tokens": 100, "overlap": 100},  # overlap must be smaller than the chunk
    {"strategy": "bogus"},
    {"min_score": 2},
])
def test_invalid_rag_config_rejected(client, bad):
    current = client.get("/config/rag").json()["settings"]
    assert client.put("/config/rag", json={**current, **bad}).status_code == 422


def test_llm_config_roundtrip_and_no_api_key_field(client):
    cfg = client.get("/config/llm").json()
    assert "api_key" not in json.dumps(cfg).lower()
    cfg["ollama"]["model"] = "other-model"
    assert client.put("/config/llm", json=cfg).json()["ollama"]["model"] == "other-model"
    assert client.get("/config/llm").json()["ollama"]["model"] == "other-model"


def test_upload_indexes_document(client):
    r = upload(client)
    assert r.status_code == 202
    docs = client.get("/documents").json()  # background indexing has finished by now
    assert docs[0]["filename"] == "france.md" and docs[0]["status"] == "ready" and docs[0]["chunks"] >= 1


def test_upload_rejects_bad_type_and_oversize(client, monkeypatch):
    assert upload(client, "evil.exe", b"x").status_code == 400
    monkeypatch.setattr(main, "MAX_UPLOAD_BYTES", 10)
    assert upload(client, "big.txt", b"x" * 11).status_code == 413


def test_upload_path_traversal_is_neutralised(client, tmp_path):
    upload(client, "../../escape.md", FRANCE)
    assert client.get("/documents").json()[0]["filename"] == "escape.md"
    assert (tmp_path / "uploads" / "escape.md").exists()
    assert not (tmp_path.parent / "escape.md").exists()


def test_query_streams_sources_tokens_done(client):
    upload(client)
    ev = events(client.post("/query", json={"question": "What is the capital of France?"}))
    names = [n for n, _ in ev]
    assert names[0] == "sources" and names[-1] == "done" and "token" in names
    assert ev[0][1][0]["source"] == "france.md"


def test_query_off_topic_skips_llm(client):
    upload(client)
    ev = events(client.post("/query", json={"question": "How do I bake sourdough bread?"}))
    assert ev[0] == ("sources", [])
    assert "don't know" in ev[1][1]


def test_query_retrieval_only_and_debug_prompt(client):
    upload(client)
    q = {"question": "What is the capital of France?"}
    only = events(client.post("/query", json={**q, "retrieval_only": True}))
    assert [n for n, _ in only] == ["sources", "done"]
    dbg = events(client.post("/query", json={**q, "debug": True}))
    prompt = next(d for n, d in dbg if n == "prompt")
    assert "Eiffel Tower" in prompt["user"] and "[1]" in prompt["user"]


def test_ollama_down_is_reported_as_error_event(client):
    upload(client)
    cfg = client.get("/config/llm").json()
    cfg["provider"], cfg["ollama"]["host"] = "ollama", "http://127.0.0.1:9"  # nothing listens here
    client.put("/config/llm", json=cfg)
    ev = events(client.post("/query", json={"question": "What is the capital of France?"}))
    assert ev[-2][0] == "error" and "Cannot reach Ollama" in ev[-2][1] and ev[-1][0] == "done"


def test_changing_index_settings_flags_reindex_and_reindex_clears_it(client):
    cur = client.get("/config/rag").json()["settings"]
    # With no documents yet there is nothing stale, so no flag.
    assert client.put("/config/rag", json={**cur, "chunk_tokens": 120}).json()["needs_reindex"] is False
    upload(client)
    # top_k only affects retrieval, not stored vectors: no flag.
    assert client.put("/config/rag", json={**cur, "chunk_tokens": 120, "top_k": 2}).json()["needs_reindex"] is False
    # chunk size changes the stored vectors: flag.
    assert client.put("/config/rag", json={**cur, "chunk_tokens": 80}).json()["needs_reindex"] is True
    assert client.post("/reindex").json() == {"queued": 1}
    assert client.get("/config/rag").json()["needs_reindex"] is False
    assert client.get("/documents").json()[0]["status"] == "ready"


def test_delete_removes_document_and_its_vectors(client):
    upload(client)
    doc_id = client.get("/documents").json()[0]["id"]
    assert client.delete(f"/documents/{doc_id}").status_code == 204
    assert client.get("/documents").json() == []
    ev = events(client.post("/query", json={"question": "What is the capital of France?"}))
    assert ev[0] == ("sources", [])
    assert client.delete(f"/documents/{doc_id}").status_code == 404
