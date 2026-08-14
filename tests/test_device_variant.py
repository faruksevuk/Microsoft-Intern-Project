import sys
from pathlib import Path
from types import SimpleNamespace


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


def test_gpu_setup_requests_only_cuda_provider(monkeypatch):
    monkeypatch.setattr(engine, "PRAG_DEVICE", "auto")
    requested = []

    class Manager:
        def discover_eps(self):
            return [SimpleNamespace(name="CUDAExecutionProvider", is_registered=False)]

        def download_and_register_eps(self, names):
            requested.append(names)
            return SimpleNamespace(registered_eps=["CUDAExecutionProvider"])

    instance = object.__new__(engine.MemoryEngine)
    instance.manager = Manager()
    instance._ensure_gpu_eps()

    assert requested == [["CUDAExecutionProvider"]]
