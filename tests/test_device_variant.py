import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import engine


class Variant:
    def __init__(self, identifier):
        self.id = identifier


class Model:
    def __init__(self):
        self.variants = [Variant("qwen-generic-cpu:1"), Variant("qwen-cuda-gpu:1")]
        self.selected = self.variants[1]

    @property
    def id(self):
        return self.selected.id

    def select_variant(self, variant):
        self.selected = variant


def test_cpu_mode_overrides_a_cached_gpu_variant(monkeypatch):
    monkeypatch.setattr(engine, "PRAG_DEVICE", "cpu")
    model = Model()

    assert engine.MemoryEngine._select_device_variant(model) == "cpu"
    assert model.id == "qwen-generic-cpu:1"
