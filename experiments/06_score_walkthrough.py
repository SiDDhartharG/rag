from pathlib import Path

import numpy as np

from rag.chunking import fixed_chunks
from rag.embeddings import embed
from rag.loaders import load_dir

doc = load_dir(Path("data"))[0]
chunks = fixed_chunks(doc.text, 200, 40)
question = "What programming languages and tools does he know?"

# Step 1: embed everything
chunk_vecs = embed(chunks)  # shape (num_chunks, 384)
qv = embed([question])[0]  # shape (384,)
print(f"chunk_vecs shape: {chunk_vecs.shape}  question vector shape: {qv.shape}")

# Step 2: score ONE chunk by hand: multiply the 384 numbers pairwise, then add them up
print("\nScoring chunk 0 by hand:")
products = chunk_vecs[0] * qv
print(f"  first 5 products: {np.round(products[:5], 4)}  ... (384 of them)")
print(f"  sum of all 384 products = {products.sum():.4f}")
print(f"  same thing with @       = {float(chunk_vecs[0] @ qv):.4f}")

# Step 3: score ALL chunks at once with one matrix multiply
scores = chunk_vecs @ qv
print("\nScore for every chunk (this is what `argmax` looks at):")
for i in np.argsort(-scores):
    bar = "#" * int(scores[i] * 100)
    print(f"  chunk {i}: {scores[i]:.3f} {bar}   {chunks[i][:45].replace(chr(10), ' ')!r}")
print(f"\nargmax -> chunk {int(np.argmax(scores))}")
