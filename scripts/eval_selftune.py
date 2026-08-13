"""Phase-2 verification: does the self-tuning policy converge REL_FLOOR to a better
operating point from citation feedback? Gold oracle: the model 'cites' the gold answer
when it's retrieved. Over rounds the controller should tighten from over-retrieval
(k shrinks, precision up) while hit@1 and gold-retrieval hold. Isolated; brain untouched.
"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from config import Config
from engine import MemoryEngine

FR = "foundry-rag-20260716-174356"
QS = [
    ("Who is the owner and what has he built?", {"owner"}),
    ("What are the owner's working preferences and style?", {"owner"}),
    ("Did we decide to use cloud models or stay fully local?", {"chat-2026-07-15-231121"}),
    ("How are memory importance scores decided in this system?", {"rule-scoring"}),
    ("Where does the foundry-rag project live on disk?", {f"{FR}-pointer", FR}),
    ("Which embedding model does foundry-rag use?", {f"{FR}-tech-stack"}),
    ("How does the foundry-rag retrieval pipeline work?", {f"{FR}-architecture"}),
    ("What UI and UX approach does foundry-rag take?", {f"{FR}-ui-ux-patterns"}),
    ("What design patterns appear in the foundry-rag codebase?", {f"{FR}-design-patterns"}),
    ("What is the core idea behind the foundry-rag project?", {f"{FR}-idea", FR}),
    ("What is still missing or TODO in foundry-rag?", {f"{FR}-missings-todos"}),
    # was "Is SQLite used anywhere in the stack?" — that claim was false and is corrected
    ("What does the stack run on and how are memories stored?", {f"{FR}-tech-stack", f"{FR}-architecture"}),
    ("If I forget where the base project folder is, which note points to it?", {f"{FR}-pointer", FR}),
]

# reads the REAL corpus (measurement only, no writes) but keeps its tuning state in a
# scratch cache, so a policy experiment never overwrites the owner's learned floor
CFG = Config(cache_dir=Path(__file__).resolve().parent / "selftuneeval")
CFG.cache_dir.mkdir(parents=True, exist_ok=True)
if CFG.policy_path.exists():
    CFG.policy_path.unlink()

e = MemoryEngine(config=CFG)
e._mark_used = lambda picked: None                       # don't mutate the brain


def run(start_floor, rounds, label):
    e._policy = {"rel_floor": start_floor, "retrieved": 0, "cited": 0, "misses": 0, "n": 0, "history": []}
    e.rel_floor = start_floor
    print(f"\n== {label} (start floor {start_floor}) ==")
    print(f"{'round':<6} {'floor':>6} {'avg_k':>6} {'hit@1':>6} {'gold_ret':>9}   tune")
    for rnd in range(rounds):
        h1 = gold = 0
        ks = []
        for q, exp in QS:
            picked = e._select_memories(e._embed(q), q)
            ids = [m["meta"].get("id") for m in picked]
            ks.append(len(picked))
            gret = any(i in exp for i in ids)
            gold += 1 if gret else 0
            h1 += 1 if (ids and ids[0] in exp) else 0
            e._record_retrieval_feedback(len(picked), 1 if gret else 0)   # oracle: cite gold if retrieved
        res = e.tune_policy()
        print(f"{rnd:<6} {e.rel_floor:>6.2f} {sum(ks)/len(ks):>6.1f} {h1/len(QS):>6.2f} {gold/len(QS):>9.2f}   {res['reason']}")


run(0.30, 8, "A: over-retrieving -> should TIGHTEN")
run(0.48, 6, "B: too tight (golds dropping) -> should LOOSEN")
