from rag.embeddings import get_model

model = get_model()
tok = model.tokenizer
params = sum(p.numel() for p in model.parameters())

print(model)
print(f"\nParameters: {params:,}  (~{params / 1e6:.0f}M)")
print(f"Max input length: {model.max_seq_length} tokens (longer text is silently truncated!)")
print(f"Output size: {model.get_sentence_embedding_dimension()} numbers")
print(f"Vocabulary: {tok.vocab_size:,} word pieces")

text = "I love cooking spaghetti"
print(f"\nTokenizer pieces: {tok.tokenize(text)}")
print(f"Token ids:        {tok(text)['input_ids']}")
