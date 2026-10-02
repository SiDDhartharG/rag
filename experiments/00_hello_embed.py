from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")
vec = model.encode("RAG retrieves relevant text before the LLM answers.")
print("shape:", vec.shape)
print("first 5 values:", vec[:5])
