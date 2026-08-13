"""Report the active curated validation gate against the current local retriever.

Unlike a unit test, this loads Foundry Local and the private corpus. It is deliberately
manual: it produces evidence for README/release notes without changing memory or policy.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from engine import MemoryEngine


def main():
    engine = MemoryEngine()
    tasks = engine.gate_tasks()
    if not tasks:
        raise SystemExit(f"No curated gate at {engine.cfg.gate_tasks_path}")
    rows = []
    for task in tasks:
        picked = engine._select_memories(engine._embed(task["q"]), task["q"])
        got = picked[0]["meta"].get("id") if picked else None
        rows.append({"id": task.get("id", task["q"][:40]), "expect": task["expect"],
                     "got": got, "hit": got in task["expect"]})
    score = sum(row["hit"] for row in rows) / len(rows)
    report = {"timestamp": datetime.now().isoformat(timespec="seconds"),
              "model": engine.chat_label, "tasks": len(rows), "hit_at_1": score, "rows": rows}
    out = Path(__file__).resolve().parent / "eval_gate_report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"GATE: {sum(r['hit'] for r in rows)}/{len(rows)} hit@1 = {score:.3f} | {engine.chat_label}")
    for row in rows:
        print(f"{'OK' if row['hit'] else 'MISS'} {row['id']}: {row['got']}")
    print(f"report -> {out.name}")


if __name__ == "__main__":
    main()
