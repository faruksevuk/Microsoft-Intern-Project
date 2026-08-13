import engine
import threading


def bare_engine(tmp_path):
    instance = object.__new__(engine.MemoryEngine)
    instance.cfg = engine.Config(root=tmp_path)
    instance.memories = []
    instance._state_lock = threading.RLock()
    return instance


def test_guarded_fails_closed_without_curated_tasks(tmp_path):
    instance = bare_engine(tmp_path)
    changed = []
    result = instance.guarded("repair", lambda: changed.append(True), lambda: changed.pop())
    assert result.action == "blocked"
    assert changed == []


def test_online_monitoring_never_creates_gate_file(tmp_path):
    instance = bare_engine(tmp_path)
    assert instance._mint_online_task("a sufficiently descriptive live query", "memory-1")
    assert instance.cfg.online_tasks_path.exists()
    assert not instance.cfg.gate_tasks_path.exists()


def test_non_format_ability_cannot_evolve_or_adopt(tmp_path):
    instance = bare_engine(tmp_path)
    memory = {"meta": {"type": "ability", "kind": "domain"}, "body": "- inspect evidence"}
    instance._find = lambda _: memory
    report = instance.evolve_ability("ability-domain")
    assert report["blocked"]
    outcome = instance.adopt_evolution("ability-domain", "- changed")
    assert not outcome["adopted"]
    assert "no task-level evaluator" in outcome["reason"]
