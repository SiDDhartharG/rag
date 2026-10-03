from rag.embeddings import embed


def compare(anchor: str, others: list[str]) -> None:
    vecs = embed([anchor] + others)
    print(f"\nvs {anchor!r}")
    for text, v in sorted(zip(others, vecs[1:]), key=lambda p: -float(vecs[0] @ p[1])):
        print(f"  {float(vecs[0] @ v):.2f}  {text!r}")


print("=" * 60 + "\n1. Single words: learned from context, not a dictionary\n" + "=" * 60)
compare("spaghetti", ["pasta", "noodles", "pizza", "Italy", "laptop", "xqzvb"])
compare("king", ["queen", "monarch", "prince", "banana"])

print("\n" + "=" * 60 + "\n2. Same word, different meaning: context decides\n" + "=" * 60)
compare("I deposited money at the bank", [
    "The bank approved my loan",       # same sense
    "We had a picnic on the river bank",  # different sense, same word
    "I went to withdraw cash",         # same sense, no shared word
])

print("\n" + "=" * 60 + "\n3. Why 'pasta' beat the paraphrase: extra words shift the vector\n" + "=" * 60)
compare("I love cooking pasta", [
    "pasta",
    "Making spaghetti is my favourite hobby",
    "Making spaghetti",
    "I enjoy making spaghetti",
])
