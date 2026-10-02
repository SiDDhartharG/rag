from pathlib import Path

import tiktoken

from rag.chunking import fixed_chunks
from rag.loaders import load_dir

enc = tiktoken.get_encoding("cl100k_base")
SIZE, OVERLAP = 200, 40
STEP = SIZE - OVERLAP

doc = load_dir(Path("data"))[0]
ids = enc.encode(doc.text)
chunks = fixed_chunks(doc.text, SIZE, OVERLAP)
chunk_ids = [enc.encode(c) for c in chunks]

print(f"Document: {len(ids)} tokens, step = {STEP}, expected starts: {list(range(0, len(ids), STEP))}")
print(f"Chunks produced: {len(chunks)}, sizes: {[len(c) for c in chunk_ids]}\n")

print("CHECK 1: every chunk starts at the expected token offset")
for i, c in enumerate(chunk_ids):
    start = i * STEP
    ok = c == ids[start : start + SIZE]
    print(f"  chunk {i}: tokens [{start}:{start + len(c)}]  matches source: {ok}")

print("\nCHECK 2: overlap - last 40 tokens of chunk i == first 40 tokens of chunk i+1")
for i in range(len(chunks) - 1):
    a, b = chunk_ids[i][-OVERLAP:], chunk_ids[i + 1][:OVERLAP]
    print(f"  chunk {i} -> {i + 1}: {a == b}")
print("  Example, chunk 0 end vs chunk 1 start:")
print(f"    end of 0:   {enc.decode(chunk_ids[0][-OVERLAP:])[:90]!r}")
print(f"    start of 1: {enc.decode(chunk_ids[1][:OVERLAP])[:90]!r}")

print("\nCHECK 3: nothing lost - stitch chunks (dropping overlap) and compare to the original")
stitched = chunk_ids[0] + [t for c in chunk_ids[1:] for t in c[OVERLAP:]]
print(f"  stitched == original tokens: {stitched == ids}")

print("\nCHECK 4: edge case - does the final chunk add anything new?")
for n in [250, 360, 361, 399, 400, 401, 1036]:
    got = fixed_chunks(enc.decode(ids[:n]), SIZE, OVERLAP)  # first n tokens of the real doc
    sizes = [len(enc.encode(c)) for c in got]
    print(f"  {n:>4} tokens -> {len(got)} chunks {sizes}" + ("  <-- last chunk is only overlap (pure duplicate)" if len(sizes) > 1 and sizes[-1] <= OVERLAP else ""))

print("\nCHECK 5: multi-byte text (Hindi) cut at token boundaries")
hindi = "नमस्ते दुनिया, यह एक परीक्षण है। " * 30
for c in fixed_chunks(hindi, 50, 10):
    if "�" in c:
        print("  broken character (U+FFFD) found in a chunk")
        break
else:
    print("  no broken characters")
