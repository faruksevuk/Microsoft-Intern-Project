"""Every filesystem location the brain uses, in one injectable object.

This is the line between a script and a library. With paths as module constants,
an embedding application (or an eval run) can only redirect them by reassigning
globals — `engine.CACHE_PATH = ...` — which is a monkey-patch, order-dependent and
invisible to the type checker. With a Config, a host app just says where its data
lives and can run several brains side by side in one process.

Defaults reproduce the original single-app layout, so existing installs are unchanged.
"""
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parent.parent


class Config:
    """Where one brain keeps its data.

    root        - the workspace; everything else defaults inside it
    memory_dir  - the markdown memory tree (the brain itself; portable, diffable)
    cache_dir   - derived state: embeddings, policy, gate tasks, logs. Deleting it
                  costs recomputation, never knowledge.
    """

    def __init__(self, root=None, memory_dir=None, cache_dir=None):
        self.root = Path(root) if root else DEFAULT_ROOT
        self.memory_dir = Path(memory_dir) if memory_dir else self.root / "memory"
        self.cache_dir = Path(cache_dir) if cache_dir else self.root / "cache"
        self.chats_dir = self.root / "chats"
        self.decks_dir = self.root / "decks"
        self.cache_path = self.cache_dir / "embeddings.json"
        self.policy_path = self.cache_dir / "policy.json"
        # v2 intentionally does not reuse the old auto-seeded gate_tasks.json.
        # A clean path prevents historical live-use tasks from masquerading as held-out.
        self.gate_tasks_path = self.cache_dir / "gate_tasks.v2.json"
        self.online_tasks_path = self.cache_dir / "online_monitoring_tasks.json"
        self.evolution_path = self.cache_dir / "evolution.json"
        self.health_log = self.cache_dir / "health.log"
        self.decisions_log = self.cache_dir / "decisions.jsonl"

    @property
    def rules_path(self):
        """The scoring constitution is a MEMORY, not config — it moves with the brain."""
        return self.memory_dir / "rules" / "scoring.md"

    @property
    def archive_dir(self):
        """Forgetting is a move, never a delete."""
        return self.memory_dir / ".archive"

    def scratch(self, name):
        """A throwaway sibling workspace (eval runs, tests) that shares nothing with
        the real brain — the honest way to measure without touching the owner's data."""
        return Config(root=self.root / "_scratch" / name)

    def __repr__(self):
        return f"Config(root={self.root!s}, memory_dir={self.memory_dir!s})"
