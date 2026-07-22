"""Verify the two advanced capabilities:
  #1 run_consolidation  -> self-training maintenance: health before/after, repairs, flags
  #2 answer_reasoned    -> test-time reasoning: grounding vs one-shot on the same questions
Runs on an isolated copy of the brain; the real memory is never touched.
"""
import shutil
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"D:\project-rag\src")
import store
import engine as eng
from engine import MemoryEngine, cosine

SCRATCH = Path(__file__).parent / "adveval"
REAL_MEM = Path(r"D:\project-rag\memory")


def point(e, dst):
    store.MEMORY_DIR = dst
    eng.MEMORY_DIR = dst
    eng.RULES_PATH = dst / "rules" / "scoring.md"
    eng.CACHE_PATH = SCRATCH / "cache.json"
    e._cache = e._load_cache()
    e.reload_memories()


def grounding(e, ans, bodies):
    sents = [s.strip() for s in ans.replace("\n", " ").split(". ") if len(s.strip()) > 25][:6]
    if not sents:
        return 0.0
    bv = [e._embed_cached(b) for b in bodies]
    ok = sum(1 for s in sents if max((cosine(e._embed(s), v) for v in bv), default=0) >= 0.60)
    return ok / len(sents)


def one_shot(e, query):
    picked = e._select_memories(e._embed(query), query)
    ctx = "\n\n".join(f"[{e._mem_path(m)}]\n{m['body']}" for m in picked)
    ans = e._complete_safe([
        {"role": "system", "content": "Answer using ONLY the context. If it lacks the answer, say you don't know.\n\nContext:\n" + ctx},
        {"role": "user", "content": query},
    ]).strip()
    return ans, [m["body"] for m in picked]


def main():
    SCRATCH.mkdir(exist_ok=True)
    dst = SCRATCH / "corpus"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(REAL_MEM, dst)

    print("loading model once...", flush=True)
    e = MemoryEngine()
    point(e, dst)

    print("\n===== #1 SELF-TRAINING CONSOLIDATION =====", flush=True)
    rep = e.run_consolidation(auto=True, deep=True)
    print(f"health: {rep['health_before']}% -> {rep['health_after']}%")
    print(f"repaired ({len(rep['repaired'])}):")
    for r in rep["repaired"]:
        print(f"   {r['id']}: rank {r['old_rank']} -> {r['new_rank']}")
    print(f"conflicts flagged: {rep['conflicts']}")
    print(f"prune candidates: {[p['id'] for p in rep['prunable']]}")

    print("\n===== #2 TEST-TIME REASONING vs ONE-SHOT =====", flush=True)
    QS = [
        "Which embedding model does foundry-rag use, and where does the project live on disk?",
        "What is still missing in foundry-rag and what is its core idea?",
    ]
    for q in QS:
        os_ans, os_bodies = one_shot(e, q)
        trace = []
        rz_ans = e.answer_reasoned(q, trace=trace)
        subs = next((v for k, v in trace if k == "subquestions"), [])
        rz_ids = next((v for k, v in trace if k == "retrieved"), [])
        rz_bodies = [e._find(i)["body"] for i in rz_ids if e._find(i)]
        print(f"\nQ: {q}")
        print(f"  sub-questions: {subs}")
        print(f"  one-shot   grounding={grounding(e, os_ans, os_bodies):.2f}  | {os_ans[:110]!r}")
        print(f"  reasoned   grounding={grounding(e, rz_ans, rz_bodies):.2f}  | {rz_ans[:110]!r}")

    print("\nADV EVAL DONE", flush=True)


if __name__ == "__main__":
    main()
