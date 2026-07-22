"""A/B eval: S0 standard RAG (flat cosine top-4) vs S1 current engine vs S2 current-without-salience.
Isolated scratch corpora; his real brain is never touched. Prints hit@1/hit@4/MRR/context size + a
small generation sample with deterministic grounding scores."""
import shutil
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"D:\project-rag\src")

SCRATCH = Path(__file__).parent / "abeval"
REAL_MEM = Path(r"D:\project-rag\memory")
PDF = Path(r"D:\repos\Microsoft-ss\Summer School Foundry Local Plan.pdf")

import store
import engine as eng
from engine import MemoryEngine, cosine

# ---------- corpora ----------
def make_corpus(name, expanded):
    dst = SCRATCH / name
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(REAL_MEM, dst)
    if expanded:
        from app import extract_text_from_path
        _, text = extract_text_from_path(str(PDF))
        try:
            chunks = eng.chunk_text(text)
        except AttributeError:
            chunks = [text[i:i + 520] for i in range(0, len(text), 520)]
        base = dst / "sources" / "summer-school"
        base.mkdir(parents=True, exist_ok=True)
        for i, ch in enumerate(chunks[:60]):
            cid = f"summer-school-c{i+1}"
            body = ch.strip().replace("\r", "")
            summ = " ".join(body.split())[:60].replace(":", " ")
            (base / f"{cid}.md").write_text(
                "---\n"
                f"id: {cid}\nbranch: sources\nproject: summer-school\ntype: chunk\n"
                "importance_base: 40\nactivation: 100\ntags: [ingest]\n"
                f"summary: {summ}\nlinks: []\nsource: eval\ncreated: 2026-07-17\nupdated: 2026-07-17\n"
                "---\n" + body + "\n", encoding="utf-8")
    return dst


def point_engine_at(e, dst):
    store.MEMORY_DIR = dst
    eng.MEMORY_DIR = dst
    eng.RULES_PATH = dst / "rules" / "scoring.md"
    eng.CACHE_PATH = SCRATCH / "cache.json"
    e._cache = e._load_cache()
    e.reload_memories()

# ---------- golden set ----------
# (question, set of acceptable ids or prefix "summer-school")
QS = [
    ("Who is the owner and what has he built?", {"owner"}),
    ("What are the owner's working preferences and style?", {"owner"}),
    ("Did we decide to use cloud models or stay fully local?", {"chat-2026-07-15-231121"}),
    ("How are memory importance scores decided in this system?", {"rule-scoring"}),
    ("Where does the foundry-rag project live on disk?", {"foundry-rag-20260716-174356-pointer", "foundry-rag-20260716-174356"}),
    ("Which embedding model does foundry-rag use?", {"foundry-rag-20260716-174356-tech-stack"}),
    ("How does the foundry-rag retrieval pipeline work?", {"foundry-rag-20260716-174356-architecture"}),
    ("What UI and UX approach does foundry-rag take?", {"foundry-rag-20260716-174356-ui-ux-patterns"}),
    ("What design patterns appear in the foundry-rag codebase?", {"foundry-rag-20260716-174356-design-patterns"}),
    ("What is the core idea behind the foundry-rag project?", {"foundry-rag-20260716-174356-idea", "foundry-rag-20260716-174356"}),
    ("What is still missing or TODO in foundry-rag?", {"foundry-rag-20260716-174356-missings-todos"}),
    ("Is SQLite used anywhere in the stack?", {"foundry-rag-20260716-174356-tech-stack", "foundry-rag-20260716-174356-architecture"}),
    ("If I forget where the base project folder is, which note points to it?", {"foundry-rag-20260716-174356-pointer", "foundry-rag-20260716-174356"}),
]
QS_PDF = [
    ("What are the phases of the summer school plan?", "summer-school"),
    ("Which week of the plan covers chunking and ingestion of documents?", "summer-school"),
    ("What deliverables does the final phase of the summer school require?", "summer-school"),
    ("Which models does the summer school plan suggest using?", "summer-school"),
    ("How is the demo day presentation structured in the plan?", "summer-school"),
]

def expected_hit(mid, exp):
    return mid.startswith("summer-school") if exp == "summer-school" else mid in exp

# ---------- systems ----------
def s0_rank(e, q_vec, k=4):
    scored = sorted(((cosine(q_vec, e._body_vector(m)), m) for m in e.memories),
                    key=lambda x: x[0], reverse=True)
    return [m["meta"].get("id") for _, m in scored[:k]], scored[0][0]


def run_system(tag, corpus_dir, e, questions, mode, salience_on=True):
    fresh = corpus_dir.parent / (corpus_dir.name + "-" + tag)
    if fresh.exists():
        shutil.rmtree(fresh)
    shutil.copytree(corpus_dir, fresh)
    point_engine_at(e, fresh)
    old_w = eng.SALIENCE_WEIGHT
    if not salience_on:
        eng.SALIENCE_WEIGHT = 0.0
    hits1 = hits4 = 0
    rr = []
    ctx_chars = []
    t0 = time.time()
    for q, exp in questions:
        q_vec = e._embed(q)
        if mode == "s0":
            ids, _ = s0_rank(e, q_vec)
            ctx_chars.append(sum(len(e._find(i)["body"]) for i in ids if e._find(i)))
        elif mode == "twotier":
            picked = e._select_twotier(q_vec)
            ids = [m["meta"].get("id") for m in picked]
            ctx_chars.append(sum(len(m["body"]) for m in picked))
        else:  # rrf (hybrid: dense + BM25, RRF-fused, dense top-1 kept)
            picked = e._select_memories(q_vec, q)
            ids = [m["meta"].get("id") for m in picked]
            ctx_chars.append(sum(len(m["body"]) for m in picked))
        rank = next((r + 1 for r, mid in enumerate(ids) if expected_hit(mid, exp)), None)
        hits1 += 1 if rank == 1 else 0
        hits4 += 1 if rank else 0
        rr.append(1.0 / rank if rank else 0.0)
    eng.SALIENCE_WEIGHT = old_w
    n = len(questions)
    return {"tag": tag, "hit@1": hits1 / n, "hit@4": hits4 / n, "mrr": sum(rr) / n,
            "ctx": sum(ctx_chars) / n, "sec": time.time() - t0}


def table(rows, title):
    print(f"\n== {title} ==")
    print(f"{'system':<14} {'hit@1':>6} {'hit@4':>6} {'MRR':>6} {'ctx chars':>10} {'wall s':>7}")
    for r in rows:
        print(f"{r['tag']:<14} {r['hit@1']:>6.2f} {r['hit@4']:>6.2f} {r['mrr']:>6.2f} {r['ctx']:>10.0f} {r['sec']:>7.1f}")

# ---------- main ----------
SCRATCH.mkdir(exist_ok=True)
print("loading models once...", flush=True)
real = make_corpus("real", expanded=False)
e = None
store.MEMORY_DIR = real
eng.MEMORY_DIR = real
eng.RULES_PATH = real / "rules" / "scoring.md"
eng.CACHE_PATH = SCRATCH / "cache.json"
e = MemoryEngine()

rows = [
    run_system("S0-standard", real, e, QS, "s0"),
    run_system("S1-twotier", real, e, QS, "twotier"),
    run_system("S2-nosalience", real, e, QS, "twotier", salience_on=False),
    run_system("S3-hybridRRF", real, e, QS, "rrf"),
]
table(rows, f"REAL corpus ({len(QS)} questions, 11 memories)")

big = make_corpus("big", expanded=True)
questions_big = QS + QS_PDF
rows_big = [
    run_system("S0-standard", big, e, questions_big, "s0"),
    run_system("S1-twotier", big, e, questions_big, "twotier"),
    run_system("S2-nosalience", big, e, questions_big, "twotier", salience_on=False),
    run_system("S3-hybridRRF", big, e, questions_big, "rrf"),
]
table(rows_big, f"EXPANDED corpus ({len(questions_big)} questions, ~70 memories)")

# ---------- generation sample: does retrieval difference reach the answer? ----------
print("\n== generation sample (5 hard questions, S0 vs S3 contexts, phi answers) ==", flush=True)
GEN_QS = [QS[5], QS[7], QS[3], QS_PDF[2], QS_PDF[1]]

def grounding(ans, bodies):
    sents = [s.strip() for s in ans.replace("\n", " ").split(". ") if len(s.strip()) > 25][:6]
    if not sents:
        return 0.0
    bv = [e._embed_cached(b) for b in bodies]
    ok = 0
    for s in sents:
        sv = e._embed(s)
        if max(cosine(sv, v) for v in bv) >= 0.60:
            ok += 1
    return ok / len(sents)

for sysname, mode in (("S0", "s0"), ("S3", "rrf")):
    fresh = SCRATCH / f"big-gen{sysname}"
    if fresh.exists():
        shutil.rmtree(fresh)
    shutil.copytree(big, fresh)
    point_engine_at(e, fresh)
    g_tot, hit_tot = 0.0, 0
    for q, exp in GEN_QS:
        q_vec = e._embed(q)
        if mode == "rrf":
            picked = e._select_memories(q_vec, q)
        else:
            ids, _ = s0_rank(e, q_vec)
            picked = [e._find(i) for i in ids if e._find(i)]
        bodies = [m["body"] for m in picked]
        ctx = "\n\n".join(f"[{m['meta'].get('id')}] {m['body']}" for m in picked)
        ans = e._complete([
            {"role": "system", "content": "Answer only from the context. If the context lacks the answer, say you don't know.\n\nContext:\n" + ctx},
            {"role": "user", "content": q},
        ])
        g = grounding(ans, bodies)
        g_tot += g
        hit_tot += 1 if any(expected_hit(m["meta"].get("id"), exp) for m in picked) else 0
        print(f"  [{sysname}] {q[:52]:<54} grounding={g:.2f} ctx-had-answer={'Y' if any(expected_hit(m['meta'].get('id'), exp) for m in picked) else 'N'}", flush=True)
    print(f"  [{sysname}] avg grounding={g_tot/len(GEN_QS):.2f}  ctx-hit={hit_tot}/{len(GEN_QS)}")

print("\nEVAL DONE")
