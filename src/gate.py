"""Validation gate — no self-modification is KEPT unless it survives a held-out check.

Why this exists: Microsoft SkillOpt (arXiv 2605.23904) ran the controlled ablation.
Ungated nightly self-evolution let a weak model adopt a plausible-but-wrong rule and
collapse from 0.554 to 0.026 (-52.8 pts) over five nights; the gated twin rejected
every one of those edits and lost nothing (0.570 -> 0.570).

Our system self-modifies in exactly that unattended way - desire-path traces, the
self-tuned retrieval floor, and consolidation repairs - with band clamps but, until
now, no measured accept/reject decision. This module supplies it.
"""
import json
from dataclasses import dataclass
from pathlib import Path

EPS = 1e-9


@dataclass(frozen=True)
class GateResult:
    action: str          # "accept" | "reject" | "ungated"
    label: str
    before: float
    after: float

    def __bool__(self):
        return self.action != "reject"

    def summary(self):
        if self.action == "ungated":
            return f"{self.label}: ungated (no held-out tasks)"
        arrow = f"{self.before:.3f} -> {self.after:.3f}"
        return f"{self.label}: {self.action.upper()} ({arrow})"


def decide(label, before, after):
    """Pure decision: keep the change unless it measurably regressed the held-out score."""
    if after + EPS < before:
        return GateResult("reject", label, before, after)
    return GateResult("accept", label, before, after)


def load_tasks(path, memories=None):
    """Held-out retrieval tasks: [{"q": ..., "expect": [memory-id, ...]}].

    Auto-seeded from the corpus on first use (each memory's own summary as the probe)
    so the gate works out of the box; the owner is meant to curate/extend this file
    with real questions - the more realistic the tasks, the stronger the guarantee.
    """
    p = Path(path)
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, list) and data:
                return data
        except Exception:
            pass
    tasks = []
    for m in (memories or []):
        summary = (m["meta"].get("summary") or "").strip()
        mid = m["meta"].get("id")
        if mid and len(summary) > 12:
            tasks.append({"q": summary, "expect": [mid]})
    if tasks:
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass
    return tasks
