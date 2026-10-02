from dataclasses import dataclass, field
from pathlib import Path

from pypdf import PdfReader


@dataclass
class Document:
    text: str
    metadata: dict = field(default_factory=dict)


def load_file(path: Path) -> Document:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        reader = PdfReader(path)
        text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
    elif suffix in {".txt", ".md"}:
        text = path.read_text(encoding="utf-8")
    else:
        raise ValueError(f"Unsupported file type: {path}")
    return Document(text=text, metadata={"source": path.name})


def load_dir(directory: Path) -> list[Document]:
    supported = {".pdf", ".txt", ".md"}
    files = sorted(p for p in directory.iterdir() if p.suffix.lower() in supported)
    return [load_file(p) for p in files]
