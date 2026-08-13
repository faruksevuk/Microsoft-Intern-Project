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
    action: str          # "accept" | "reject" | "blocked"
    label: str
    before: float
    after: float

    def __bool__(self):
        return self.action == "accept"

    def summary(self):
        if self.action == "blocked":
            return f"{self.label}: BLOCKED (no curated held-out tasks)"
        arrow = f"{self.before:.3f} -> {self.after:.3f}"
        return f"{self.label}: {self.action.upper()} ({arrow})"


def decide(label, before, after):
    """Pure decision: keep the change unless it measurably regressed the held-out score."""
    if after + EPS < before:
        return GateResult("reject", label, before, after)
    return GateResult("accept", label, before, after)


def load_tasks(path, memories=None):
    """Held-out retrieval tasks: [{"q": ..., "expect": [memory-id, ...]}].

    This file is deliberately *not* auto-seeded and is never changed by live usage.
    A gate is only held out when its questions were not used to tune the system. Keep
    a curated, versioned file here; live queries belong in online monitoring instead.
    """
    p = Path(path)
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, list) and data:
                return data
        except Exception:
            pass
    return []
