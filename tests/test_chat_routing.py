import threading

import engine


def bare_engine(tmp_path):
    instance = object.__new__(engine.MemoryEngine)
    instance.cfg = engine.Config(root=tmp_path)
    instance.memories = []
    instance._state_lock = threading.RLock()
    return instance


def test_normal_rag_question_never_starts_a_tool_workflow(tmp_path):
    instance = bare_engine(tmp_path)
    instance._complete_safe = lambda _: (_ for _ in ()).throw(AssertionError("router must not call the model"))

    decision = instance.decide_action("Project showcase tech stack'i nedir?")

    assert decision["action"] == "answer"
    assert decision["source"] == "rules"


def test_only_explicit_slide_creation_starts_slide_workflow(tmp_path):
    instance = bare_engine(tmp_path)

    assert instance.decide_action("Showcase projesi için sunum oluştur")["action"] == "slides"
    assert instance.decide_action("Bu sunumun tech stack'i nedir?")["action"] == "answer"
