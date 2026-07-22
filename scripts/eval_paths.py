"""Findability-over-time experiment: does the desire-path mechanism (found_by traces
wired into the hybrid ranker) let a memory be found by DRIFTED future queries after it
was used once via a differently-phrased training query?

Protocol per item: COLD = corpus with found_by stripped, query with a drifted phrasing V.
WARM = seed the answer memory's found_by with a DIFFERENT training phrasing T (V != T),
reload, query V again. If desire-paths work, WARM hit@1 > COLD hit@1. Controls (already
hit cold) check WARM doesn't regress them. Runs on an isolated copy; the real brain is
never touched.
"""
import shutil
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"D:\project-rag\src")

import store
import engine as eng
from engine import MemoryEngine
from store import patch_meta

SCRATCH = Path(__file__).parent / "pathseval"
REAL_MEM = Path(r"D:\project-rag\memory")
FR = "foundry-rag-20260716-174356"

# (answer_id, training phrasing T seeded into found_by, drifted test phrasing V)  -- V != T, both drift from the body
ITEMS = [
    (f"{FR}-tech-stack",       "what embedding model does the project run",     "which vector model powers the local search here"),
    (f"{FR}-architecture",     "how does the retrieval pipeline work end to end", "walk me through how it finds documents and returns results"),
    (f"{FR}-ui-ux-patterns",   "describe the ui and ux approach",               "what does the front end experience feel like for a user"),
    (f"{FR}-missings-todos",   "what is missing or on the todo list",           "what still needs to be built before it is done"),
    (f"{FR}-design-patterns",  "what design patterns appear in the codebase",   "what recurring coding structures show up in the source"),
]
CONTROLS = [  # already hit cold; get their OWN trace too (symmetric learning) -> must not regress
    ("owner",                    "who are you and what have you built",   "tell me about the person behind these projects"),
    ("chat-2026-07-15-231121",   "did we choose cloud or local models",   "were we going with cloud services or staying local"),
]


def point(e, dst):
    store.MEMORY_DIR = dst
    eng.MEMORY_DIR = dst
    eng.RULES_PATH = dst / "rules" / "scoring.md"
    eng.CACHE_PATH = SCRATCH / "cache.json"
    e._cache = e._load_cache()
    e.reload_memories()


def rank1(e, ans_id, query):
    e._mark_used = lambda picked: None          # do not mutate during measurement
    picked = e._select_memories(e._embed(query), query)
    ids = [m["meta"].get("id") for m in picked]
    hit1 = bool(ids) and ids[0] == ans_id
    hit4 = ans_id in ids
    return hit1, hit4, ids[:3]


def strip_found_by(dst):
    for p in dst.rglob("*.md"):
        patch_meta(p, {}, remove=("found_by",))


def main():
    SCRATCH.mkdir(exist_ok=True)
    dst = SCRATCH / "corpus"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(REAL_MEM, dst)
    strip_found_by(dst)

    print("loading model once...", flush=True)
    point_e = MemoryEngine()  # loads models with default dir first
    point(point_e, dst)
    e = point_e

    allitems = ITEMS + CONTROLS

    def measure(tag):
        h1 = h4 = 0
        rows = []
        for ans, _T, V in allitems:
            hit1, hit4, top = rank1(e, ans, V)
            h1 += hit1
            h4 += hit4
            rows.append((ans.replace(FR + "-", "fr:"), hit1, hit4, top[0] if top else "-"))
        return h1, h4, rows

    # COLD
    c1, c4, cold_rows = measure("cold")

    # seed found_by with the training phrasing T on EVERY memory (symmetric learning:
    # in real use every queried memory accumulates its own traces), reload, WARM
    for ans, T, V in allitems:
        m = e._find(ans)
        if m and T:
            patch_meta(m["path"], {"found_by": [T]})
    e.reload_memories()
    w1, w4, warm_rows = measure("warm")

    n = len(allitems)
    nd = len(ITEMS)
    print(f"\n{'item':<26} {'COLD h1':>8} {'WARM h1':>8}   cold_top1 -> warm_top1")
    for (ans, ch1, ch4, ctop), (_, wh1, wh4, wtop) in zip(cold_rows, warm_rows):
        mark = "" if ans.startswith("fr:") else "  (control)"
        print(f"{ans:<26} {('Y' if ch1 else 'n'):>8} {('Y' if wh1 else 'n'):>8}   {ctop:<20} -> {wtop}{mark}")
    print(f"\nDRIFT items ({nd}):   hit@1  COLD {c1 - _ctrl_h1(cold_rows)}/{nd}  ->  WARM {w1 - _ctrl_h1(warm_rows)}/{nd}")
    print(f"ALL items ({n}):     hit@1  COLD {c1}/{n}  ->  WARM {w1}/{n}   |   hit@4  COLD {c4}/{n} -> WARM {w4}/{n}")


def _ctrl_h1(rows):
    return sum(h1 for ans, h1, h4, top in rows if not ans.startswith("fr:"))


if __name__ == "__main__":
    main()
