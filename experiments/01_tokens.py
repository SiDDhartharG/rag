from pathlib import Path

import tiktoken

from rag.loaders import load_dir

enc = tiktoken.get_encoding("cl100k_base")

# 1. How do individual words split into tokens?
print("=== Words -> tokens ===")
for word in ["cat", "unbelievable", "Kubernetes", "React.js", "garg.sid6665@gmail.com", "नमस्ते"]:
    ids = enc.encode(word)
    pieces = [enc.decode([i]) for i in ids]
    print(f"{word!r:30} {len(ids)} tokens: {pieces}")

# 2. Characters vs tokens on real documents
print("\n=== Characters vs tokens ===")
for doc in load_dir(Path("data")):
    n_chars = len(doc.text)
    n_tokens = len(enc.encode(doc.text))
    print(f"{doc.metadata['source']}: {n_chars} chars, {n_tokens} tokens, "
          f"{n_chars / n_tokens:.2f} chars/token")

    # 3. Show the first 25 tokens as the model sees them
    print("First 25 tokens:", [enc.decode([i]) for i in enc.encode(doc.text)[:25]])
