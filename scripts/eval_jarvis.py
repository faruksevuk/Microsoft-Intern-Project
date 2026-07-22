"""Verify the Jarvis layer: acquire_ability -> save_ability -> apply_ability, and
research_answer. Distill/apply use the local model; the web fetch is MOCKED so the
logic is verified deterministically, then one LIVE research call is attempted (best-effort)."""
import shutil
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"D:\project-rag\src")
import store
import engine as eng
import research
from engine import MemoryEngine

SCRATCH = Path(__file__).parent / "jarviseval"
CANNED = {
    "source": "Investopedia - Fundamental Analysis",
    "url": "https://www.investopedia.com/terms/f/fundamentalanalysis.asp",
    "text": ("Fundamental analysis evaluates a stock's intrinsic value by examining the company's "
             "financial statements, its industry, and the broader economy. Analysts study the income "
             "statement, balance sheet, and cash-flow statement, then compute ratios such as the "
             "price-to-earnings (P/E) ratio, earnings per share (EPS), debt-to-equity, and return on "
             "equity. They also assess management quality, competitive moat, and macroeconomic "
             "conditions. The result is compared to the current market price to decide whether the "
             "stock is undervalued or overvalued. For example, in 2024 a company trading at a P/E of 8 "
             "while peers averaged 15 might be considered undervalued."),
}


def main():
    SCRATCH.mkdir(exist_ok=True)
    dst = SCRATCH / "corpus"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(Path(r"D:\project-rag\memory"), dst)
    store.MEMORY_DIR = dst
    eng.MEMORY_DIR = dst
    eng.RULES_PATH = dst / "rules" / "scoring.md"
    eng.CACHE_PATH = SCRATCH / "cache.json"
    eng.POLICY_PATH = SCRATCH / "policy.json"

    print("loading model once...", flush=True)
    e = MemoryEngine()
    e._cache = e._load_cache()
    e.reload_memories()

    # ---- MOCK the web so distill/save/apply are verified deterministically ----
    research.research = lambda q, **k: CANNED

    print("\n== acquire_ability('do fundamental analysis of a stock') ==", flush=True)
    draft = e.acquire_ability("do fundamental analysis of a stock")
    print("METHOD (distilled, should be steps, NO 2024/prices):")
    print("  " + draft["method"].replace("\n", "\n  "))
    print("source:", draft["source"])

    aid = e.save_ability("stock fundamental analysis", draft["method"], draft["source"])
    m = e._find(aid)
    print(f"\n== saved ability: id={aid}  type={m['meta'].get('type')}  branch={m['meta'].get('branch')} ==")

    print("\n== apply_ability to fresh (volatile) data ==", flush=True)
    live_data = "THYAO: price 250 TL, P/E 6.2, EPS 40, debt/equity 0.9, sector avg P/E 11, up 12% this month."
    analysis = e.apply_ability(aid, live_data, "is THYAO undervalued on fundamentals?")
    print("  " + (analysis or "(none)")[:400].replace("\n", "\n  "))

    print("\n== research_answer (still mocked) ==", flush=True)
    ra = e.research_answer("what is fundamental analysis")
    print("  answer:", ra["answer"][:200].replace("\n", " "))
    print("  source:", ra["source"])

    # ---- one LIVE research attempt (best-effort; network may be flaky here) ----
    print("\n== LIVE research attempt (best-effort) ==", flush=True)
    import importlib
    importlib.reload(research)          # restore real research.research
    eng.research = research
    live = research.research("what is retrieval augmented generation")
    print("  live fetch:", (live["source"][:60] + " | " + live["url"]) if live else "no result (network/rate-limit)")

    print("\nJARVIS EVAL DONE", flush=True)


if __name__ == "__main__":
    main()
