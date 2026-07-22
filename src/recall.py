import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from store import load_all

from foundry_local_sdk import Configuration, FoundryLocalManager

EMBED_MODEL = "qwen3-embedding-0.6b"
CHAT_MODEL = "qwen2.5-1.5b"
TOP_K = 3

SYSTEM_PROMPT = """You are a local memory assistant. Answer using ONLY the memories below. If they don't contain enough information, say you don't know.

Reason briefly before answering: (1) the goal, (2) which memories matter, (3) connect them, (4) the grounded answer.

Memories:
{context}"""


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


def main():
    sys.stdout.reconfigure(encoding="utf-8")

    FoundryLocalManager.initialize(Configuration(app_name="project_rag"))
    manager = FoundryLocalManager.instance

    embed_model = manager.catalog.get_model(EMBED_MODEL)
    embed_model.download(lambda p: print(f"\rEmbedding model: {p:.1f}%", end="", flush=True))
    print()
    embed_model.load()
    embedder = embed_model.get_embedding_client()

    chat_model = manager.catalog.get_model(CHAT_MODEL)
    chat_model.download(lambda p: print(f"\rChat model: {p:.1f}%", end="", flush=True))
    print()
    chat_model.load()
    chat = chat_model.get_chat_client()

    memories = load_all()
    if not memories:
        print("No memories found under memory/. Add some first.")
        return
    vectors = [item.embedding for item in embedder.generate_embeddings([m["body"] for m in memories]).data]

    print(f"\n{len(memories)} memories ready. Ask a question (exit/quit to stop).\n")

    while True:
        query = input("Question: ").strip()
        if query.lower() in ("exit", "quit"):
            break
        if not query:
            continue

        q_vec = embedder.generate_embedding(query).data[0].embedding
        scored = sorted(
            ((cosine(q_vec, v), m) for v, m in zip(vectors, memories)),
            key=lambda x: x[0], reverse=True,
        )
        context = "\n\n".join(f"[{m['meta'].get('id', '?')}] {m['body']}" for _, m in scored[:TOP_K])

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT.format(context=context)},
            {"role": "user", "content": query},
        ]

        print("\nAnswer: ", end="", flush=True)
        for chunk in chat.complete_streaming_chat(messages):
            if chunk.choices and chunk.choices[0].delta.content:
                print(chunk.choices[0].delta.content, end="", flush=True)
        print("\n")

    embed_model.unload()
    chat_model.unload()


if __name__ == "__main__":
    main()
