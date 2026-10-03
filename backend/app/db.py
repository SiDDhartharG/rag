"""SQLite storage: one row of settings, and one row per uploaded document."""

from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.engine import Engine
from sqlmodel import Field, Session, SQLModel, create_engine

DEFAULT_DB_PATH = Path("data/app.db")


class Settings(SQLModel, table=True):
    """Always a single row (id=1). The two JSON columns hold RagSettings and LLMSettings."""

    id: int = Field(default=1, primary_key=True)
    rag_json: str
    llm_json: str
    needs_reindex: bool = False


class Document(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    filename: str = Field(unique=True, index=True)
    status: str = "pending"  # pending -> indexing -> ready | failed
    chunks: int = 0
    error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


def make_engine(path: Path = DEFAULT_DB_PATH) -> Engine:
    path.parent.mkdir(parents=True, exist_ok=True)
    # check_same_thread=False: FastAPI runs sync routes and background tasks in different threads.
    engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    return engine


def session_for(engine: Engine) -> Session:
    return Session(engine)
