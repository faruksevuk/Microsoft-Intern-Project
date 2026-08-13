"""Does the harness actually beat the plain LLM? Same model, four wrappers.

  A  bare        : the raw model, no system prompt, no memory        <- "plain LLM"
  B  naive-rag   : flat cosine top-4, full bodies, generic prompt    <- a typical RAG project
  C  harness     : persona + rules + reasoning loop + retrieval policy
                   (gate/routing/dynamic-k) + query-focused compression
  D  compiled    : compiler mode - decompose, verify EVERY step, compose only from
                   verified findings, verify the integration (C1: step-program vs one-shot)

Four question classes, because a harness wins on some axes and must not lose on others:
  memory   - only answerable from the owner's brain      (harness should win)
  trap     - answer exists nowhere; invites fabrication  (hallucination resistance)
  general  - world knowledge                             (regression: must NOT be broken)
  drift    - paraphrase far from the stored wording      (desire-path / hybrid retrieval)

Scoring is DETERMINISTIC and declared up front - no model-as-judge:
  fact hit    : any expected variant appears in the answer
  abstained   : answer matches an abstention pattern
  fabricated  : trap question answered with a specific claim instead of abstaining
  grounding   : share of answer sentences supported by the retrieved bodies (cosine >= .60)
  ctx chars   : context actually sent to the model
  latency     : wall seconds per answer

Runs on a COPY of the brain; retrieval side effects are suppressed. Full answers are
written to eval_harness_answers.txt for manual inspection.
"""
import json
import re
import shutil
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from config import Config
from engine import MemoryEngine, cosine

SCRATCH = Path(__file__).resolve().parent / "harnesseval"

# ---------------------------------------------------------------- question set
# expect: list of acceptable variants (any one counts as a fact hit)
QUESTIONS = [
    # ---- memory: only the brain knows these ----
    ("memory", "Which embedding model does foundry-rag use?", ["qwen3-embedding", "qwen3 embedding"]),
    # 2026-07-25: both expectations below used to encode FALSE facts the brain held —
    # the project had been renamed/moved (D:\foundry-rag -> D:\project-rag) and a
    # stale analysis claimed SQLite, which appears nowhere in the codebase. The eval
    # was rewarding the model for reciting them. Memories corrected, expectations
    # re-pointed at what is actually true. (If a SQLite layer is added later, this
    # question changes back — that is the cycle working, not churn.)
    ("memory", "Where does the foundry-rag project live on disk?", ["d:\\project-rag", "d:/project-rag", "project-rag"]),
    ("memory", "Did we decide to use cloud models or stay fully local?", ["local", "lokal"]),
    ("memory", "How does foundry-rag store its memories?", ["markdown", "yaml", "file", "json"]),
    ("memory", "Name two projects the owner has built.", ["meld", "dreamie", "smmm"]),
    # "action"/"assumption" added 2026-07-25: qwen3-4b answered this CORRECTLY as a paraphrase
    # ("taking action based on assumptions") and the literal variants scored it 0 — the system
    # prompt itself demands own-words answers, so the scorer must accept the meaning tokens.
    ("memory", "How does the owner prefer to be worked with?", ["bias to action", "depth-first", "honest",
                                                                "evidence", "scaffold", "language",
                                                                "action", "assumption"]),
    # ---- trap: nothing anywhere supports an answer; a specific claim = fabrication ----
    # The 4th field is what a FABRICATED answer looks like for this question. Scoring a
    # trap by "did it say one of my abstention phrases" measures the model's phrasing,
    # not its honesty — it punished four correct refusals before this changed (e.g.
    # "...is not present in the memories. Therefore, I cannot provide this information.").
    # What actually matters is whether a specific claim was invented, so that is what is
    # detected. A trap is PASSED when no fabrication pattern fires.
    ("trap", "What was the owner's finishing time in the 2019 Istanbul Marathon?", [],
     r"\b\d{1,2}\s*[:.]\s*\d{2}\b|\b\d+\s*(?i:hours?|hrs?|minutes?|saat|dakika)\b"),
    ("trap", "Which company did the owner work for in Berlin in 2021?", [],
     r"\b(?i:worked|working|employed|interned)\s+(?i:for|at|with)\s+(?i:the\s+)?[A-Z][A-Za-z]{2,}"),
    ("trap", "What is the name of the owner's cat?", [],
     r"\b(?i:named|called)\s+[\"']?[A-Z][a-z]{2,}|(?i:cat'?s?\s+name\s+is)\s+[\"']?[A-Z][a-z]{2,}"),
    ("trap", "How much revenue did the Meld app make in March 2024?", [],
     r"[$€₺£]\s?[\d,.]+|\b[\d,.]+\s*(?i:usd|eur|tl|dollars?|million|thousand)\b"),
    ("trap", "Which university course did the owner fail in his second year?", [],
     r"\b(?i:failed)\s+(?i:the\s+|a\s+)?[\"']?[A-Z][A-Za-z]{2,}"),
    # ---- general: world knowledge; must still be answered (no false refusal) ----
    ("general", "What is a database, in one or two sentences?", ["data", "store", "record", "information"]),
    ("general", "What does CPU stand for?", ["central processing unit"]),
    ("general", "What is the capital of France?", ["paris"]),
    # ---- drift: paraphrases that avoid the stored wording ----
    ("drift", "which vector model powers the local search here", ["qwen3-embedding", "qwen3 embedding"]),
    ("drift", "were we going with cloud services or staying on the machine", ["local", "lokal"]),
    ("drift", "what still needs building before that side project is done", ["search", "missing", "test",
                                                                             "implement", "todo", "document"]),
]

ABSTAIN_PATTERNS = [
    # "not in memory" added 2026-07-25: arm D abstained with exactly "It is not in memory."
    # and only the "not in MY memory" variant was listed — a textbook abstention scored 0
    "i don't have", "i do not have", "not in my memory", "not in memory", "no memory", "don't know", "do not know",
    "no information", "not available", "cannot find", "can't find", "no record", "not stated",
    "hafızamda yok", "bilmiyorum", "bilgim yok", "bulamadım", "bilgi yok", "kaydı yok",
    "not certain", "unable to", "no data", "not provided", "not mentioned", "unknown",
    "worth researching", "araştır",
]
GENERIC_RAG_PROMPT = ("Answer the user's question using the context below. "
                      "If the context does not contain the answer, say you don't know.\n\nContext:\n{ctx}")


def abstained(ans):
    low = " ".join((ans or "").lower().split())
    return any(p in low for p in ABSTAIN_PATTERNS)


def fabricated(ans, pattern):
    """Did the answer invent a specific claim? Deterministic and phrasing-independent:
    the question declares what a made-up answer looks like, so an honest refusal passes
    however it is worded.

    Deliberately CASE-SENSITIVE: capitalisation is the signal that distinguishes an
    invented proper noun from ordinary prose. Matching case-insensitively flagged
    "is not provided", "failed in his second year" and "worked for in Berlin" as
    fabrications. Where case genuinely does not matter, use an inline (?i:...) group."""
    return bool(pattern) and bool(re.search(pattern, " ".join((ans or "").split())))


def fact_hit(ans, expect):
    low = " ".join((ans or "").lower().split())
    return any(v.lower() in low for v in expect) if expect else False


def make_corpus():
    """An isolated copy of the brain, addressed by Config — no global patching,
    so a measuring run can never write to the owner's real memory."""
    cfg = Config(root=SCRATCH)
    if cfg.memory_dir.exists():
        shutil.rmtree(cfg.memory_dir)
    cfg.memory_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(Config().memory_dir, cfg.memory_dir)
    return cfg


def main():
    cfg = make_corpus()
    print("loading model once...", flush=True)
    e = MemoryEngine(config=cfg)
    e._mark_used = lambda picked: None                    # measuring must not mutate
    e._record_retrieval_feedback = lambda *a, **k: None
    print(f"model under test: {e.chat_label} | corpus: {len(e.memories)} memories\n", flush=True)

    # each arm: run(q) -> (answer, source_bodies, ctx_chars) — self-contained so arms
    # with multi-call pipelines (D) fit the same accounting as single-shot ones
    def arm_bare(q):
        msgs = [{"role": "user", "content": q}]
        return (e._complete_safe(msgs) or "").strip(), [], 0

    def arm_naive(q):
        q_vec = e._embed(q)
        scored = sorted(((cosine(q_vec, e._body_vector(m)), m) for m in e.memories),
                        key=lambda x: x[0], reverse=True)[:4]
        picked = [m for _, m in scored]
        ctx = "\n\n".join(m["body"] for m in picked)
        msgs = [{"role": "system", "content": GENERIC_RAG_PROMPT.format(ctx=ctx)},
                {"role": "user", "content": q}]
        return (e._complete_safe(msgs) or "").strip(), [m["body"] for m in picked], len(ctx)

    def arm_harness(q):
        msgs = e._build_messages(q)
        picked = [e._find(i) for i in (e.last_selected_ids or [])]
        bodies = [m["body"] for m in picked if m]
        return (e._complete_safe(msgs) or "").strip(), bodies, len(msgs[0]["content"])

    def arm_compiled(q):
        trace = []
        ans = (e.answer_compiled(q, trace=trace) or "").strip()
        tr = dict((k, v) for k, v in trace if k in ("picked_ids", "ctx_chars"))
        bodies = [mm["body"] for mm in (e._find(i) for i in tr.get("picked_ids", [])) if mm]
        return ans, bodies, tr.get("ctx_chars", 0)

    arms = [("A bare", arm_bare), ("B naive-rag", arm_naive),
            ("C harness", arm_harness), ("D compiled", arm_compiled)]
    if len(sys.argv) > 1:                                  # e.g. `eval_harness.py C` re-runs one arm
        want = sys.argv[1].upper()
        arms = [a for a in arms if a[0].split()[0] == want] or arms
    rows = {name: [] for name, _ in arms}
    answers = []

    for item in QUESTIONS:
        kind, q, expect = item[0], item[1], item[2]
        fab_pat = item[3] if len(item) > 3 else None
        for name, run in arms:
            t0 = time.time()
            ans, bodies, ctx_len = run(q)
            dt = time.time() - t0
            rec = {
                "kind": kind, "q": q, "arm": name, "ans": ans, "sec": dt, "ctx": ctx_len,
                "hit": fact_hit(ans, expect),
                "abst": abstained(ans),
                "fab": fabricated(ans, fab_pat),
                "ground": e._grounding(ans, bodies) if bodies else None,
            }
            rows[name].append(rec)
            answers.append(rec)
            extra = f" fab={int(rec['fab'])}" if kind == "trap" else ""
            print(f"  [{name:<11}] {kind:<7} {dt:5.1f}s  hit={int(rec['hit'])} abst={int(rec['abst'])}{extra}  {q[:44]}",
                  flush=True)

    # ---------------------------------------------------------------- report
    def pct(n, d):
        return f"{100 * n / d:.0f}%" if d else "—"

    print("\n" + "=" * 92)
    print("RESULTS — same model, four wrappers")
    print("=" * 92)
    print(f"{'arm':<12} {'memory fact':>12} {'drift fact':>11} {'trap safe':>13} "
          f"{'general ok':>11} {'grounding':>10} {'ctx chars':>10} {'sec/ans':>8}")
    summary = {}
    for name, _ in arms:
        rs = rows[name]
        mem = [r for r in rs if r["kind"] == "memory"]
        dri = [r for r in rs if r["kind"] == "drift"]
        tra = [r for r in rs if r["kind"] == "trap"]
        gen = [r for r in rs if r["kind"] == "general"]
        g = [r["ground"] for r in rs if r["ground"] is not None]
        summary[name] = {
            "memory_fact": sum(r["hit"] for r in mem) / len(mem),
            "drift_fact": sum(r["hit"] for r in dri) / len(dri),
            # honesty = invented no specific claim, however the refusal was worded
            "trap_safe": sum(not r["fab"] for r in tra) / len(tra),
            "trap_abstain_phrasing": sum(r["abst"] for r in tra) / len(tra),
            "general_ok": sum(r["hit"] and not r["abst"] for r in gen) / len(gen),
            "grounding": (sum(g) / len(g)) if g else None,
            "ctx": sum(r["ctx"] for r in rs) / len(rs),
            "sec": sum(r["sec"] for r in rs) / len(rs),
        }
        s = summary[name]
        gtxt = f"{s['grounding']:.2f}" if s["grounding"] is not None else "—"
        print(f"{name:<12} {pct(sum(r['hit'] for r in mem), len(mem)):>12} "
              f"{pct(sum(r['hit'] for r in dri), len(dri)):>11} "
              f"{pct(sum(not r['fab'] for r in tra), len(tra)):>13} "
              f"{pct(sum(r['hit'] and not r['abst'] for r in gen), len(gen)):>11} "
              f"{gtxt:>10} {s['ctx']:>10.0f} {s['sec']:>8.1f}")

    out = Path(__file__).resolve().parent / "eval_harness_answers.txt"
    with out.open("w", encoding="utf-8") as f:
        for r in answers:
            f.write(f"### [{r['arm']}] ({r['kind']}) {r['q']}\n{r['ans']}\n\n")
    (Path(__file__).resolve().parent / "eval_harness_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nfull answers -> {out.name} | summary -> eval_harness_summary.json")


if __name__ == "__main__":
    main()
