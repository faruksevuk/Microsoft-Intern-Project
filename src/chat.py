import math
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from store import load_all, parse_memory, MEMORY_DIR

from foundry_local_sdk import Configuration, FoundryLocalManager

EMBED_MODEL = "qwen3-embedding-0.6b"
CHAT_MODEL = "qwen2.5-1.5b"
TOP_K = 3        # memories retrieved per turn
K_RECALL = 2     # earlier (dropped) turns retrieved per turn
MAX_TURNS = 6    # recent pairs kept verbatim (working memory)

SYSTEM_PROMPT = """You are a local memory assistant. Use the memories, the earlier conversation, and the recent messages to respond.
- If the user asks a question, answer from these sources; if the info isn't there, say you don't know.
- If the user makes a statement or is chatting, respond naturally (acknowledge, discuss) - don't refuse.
Keep answers concise.

Memories:
{memories}

Earlier in this conversation:
{earlier}"""

DISTILL_PROMPT = """Distill the conversation below for future reference. Output exactly two sections:

SUMMARY: 2-4 sentences on what was discussed.
DECISIONS: a short bullet list of concrete decisions made (one per line starting with "- "). If none, write "- none".

Conversation:
{transcript}"""


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


def top_items(q_vec, items, k):
    scored = sorted(((cosine(q_vec, it["vec"]), it) for it in items), key=lambda x: x[0], reverse=True)
    return [it for _, it in scored[:k]]


def complete(chat, messages):
    out = ""
    for chunk in chat.complete_streaming_chat(messages):
        if chunk.choices and chunk.choices[0].delta.content:
            out += chunk.choices[0].delta.content
    return out


def transcript_of(recall_turns, history):
    parts = [t["text"] for t in recall_turns]
    parts += [f"{'You' if m['role'] == 'user' else 'Assistant'}: {m['content']}" for m in history]
    return "\n".join(parts)


def save_past_chat(draft, embedder, memories, mem_vectors):
    now = datetime.now()
    mem_id = f"chat-{now:%Y-%m-%d-%H%M%S}"
    path = MEMORY_DIR / "past-chats" / f"{mem_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n"
        f"id: {mem_id}\n"
        "branch: past-chats\n"
        "type: episode\n"
        "importance_base: 50\n"
        "activation: 100\n"
        "tags: [chat, consolidation]\n"
        f"summary: Consolidated chat from {now:%Y-%m-%d %H:%M}\n"
        "links: []\n"
        "source: chat /save\n"
        f"created: {now:%Y-%m-%d}\n"
        f"updated: {now:%Y-%m-%d}\n"
        "---\n"
        f"{draft}\n",
        encoding="utf-8",
    )
    meta, body = parse_memory(path)
    memories.append({"path": path, "meta": meta, "body": body})
    mem_vectors.append(embedder.generate_embedding(body).data[0].embedding)
    return path


def main():
    sys.stdout.reconfigure(encoding="utf-8")

    FoundryLocalManager.initialize(Configuration(app_name="project_rag"))
    manager = FoundryLocalManager.instance

    print("Loading models...", flush=True)
    embed_model = manager.catalog.get_model(EMBED_MODEL)
    embed_model.download(lambda p: None)
    embed_model.load()
    embedder = embed_model.get_embedding_client()

    chat_model = manager.catalog.get_model(CHAT_MODEL)
    chat_model.download(lambda p: None)
    chat_model.load()
    chat = chat_model.get_chat_client()

    memories = load_all()
    mem_vectors = (
        [item.embedding for item in embedder.generate_embeddings([m["body"] for m in memories]).data]
        if memories else []
    )

    history = []        # recent window, verbatim
    recall_turns = []   # dropped pairs: {"text": ..., "vec": ...}
    print(f"\n{len(memories)} memories loaded. Chat - /save to consolidate, exit/quit to stop.\n")

    while True:
        query = input("You: ").strip()
        if query.lower() in ("exit", "quit"):
            break
        if not query:
            continue

        if query.lower() == "/save":
            if not history and not recall_turns:
                print("Nothing to save yet.\n")
                continue
            print("\n--- Draft (summary + decisions) ---")
            draft = complete(chat, [{"role": "user", "content": DISTILL_PROMPT.format(transcript=transcript_of(recall_turns, history))}]).strip()
            print(draft)
            print("--- end draft ---")
            if input("Save this as a past-chats memory? (y/n): ").strip().lower() == "y":
                print(f"Saved: {save_past_chat(draft, embedder, memories, mem_vectors)}\n")
            else:
                print("Discarded.\n")
            continue

        q_vec = embedder.generate_embedding(query).data[0].embedding

        if memories:
            scored = sorted(((cosine(q_vec, v), m) for v, m in zip(mem_vectors, memories)), key=lambda x: x[0], reverse=True)
            mem_context = "\n\n".join(f"[{m['meta'].get('id', '?')}] {m['body']}" for _, m in scored[:TOP_K])
        else:
            mem_context = "(none)"

        earlier = top_items(q_vec, recall_turns, K_RECALL) if recall_turns else []
        earlier_context = "\n".join(t["text"] for t in earlier) if earlier else "(none)"

        messages = (
            [{"role": "system", "content": SYSTEM_PROMPT.format(memories=mem_context, earlier=earlier_context)}]
            + history
            + [{"role": "user", "content": query}]
        )

        print("Assistant: ", end="", flush=True)
        answer = ""
        for chunk in chat.complete_streaming_chat(messages):
            if chunk.choices and chunk.choices[0].delta.content:
                token = chunk.choices[0].delta.content
                answer += token
                print(token, end="", flush=True)
        print("\n")

        history.append({"role": "user", "content": query})
        history.append({"role": "assistant", "content": answer})

        while len(history) > MAX_TURNS * 2:
            u = history.pop(0)
            a = history.pop(0)
            text = f"You: {u['content']}\nAssistant: {a['content']}"
            recall_turns.append({"text": text, "vec": embedder.generate_embedding(text).data[0].embedding})

    embed_model.unload()
    chat_model.unload()


if __name__ == "__main__":
    main()
