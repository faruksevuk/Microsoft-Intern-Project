import engine


def memory(project):
    return {"meta": {"project": project}}


def test_explicit_project_name_creates_a_hard_retrieval_scope():
    memories = [memory("foundry-rag"), memory("showcase")]

    assert engine.named_projects("what is the tech stack of the project showcase", memories) == {"showcase"}
    assert engine.named_projects("foundry rag mimarisi nedir?", memories) == {"foundry-rag"}


def test_stream_filter_never_reveals_reasoning_tokens():
    assert engine.visible_stream_text("<thi") == ""
    assert engine.visible_stream_text("<think>working") == ""
    assert engine.visible_stream_text("<think>working</think>\nAnswer") == "Answer"
    assert engine.visible_stream_text("Answer") == "Answer"


def test_chat_boundary_never_writes_retrieval_examples(tmp_path):
    instance = object.__new__(engine.MemoryEngine)
    instance.cfg = engine.Config(root=tmp_path)
    instance.memories = []

    assert instance._wear_paths("what is showcase", "A plausible answer.") == []
    assert not instance.cfg.online_tasks_path.exists()


def test_package_manifest_stack_facts_are_exact(tmp_path):
    (tmp_path / "package.json").write_text(
        '{"dependencies":{"next":"16.3.0","react":"19.2.3"},'
        '"devDependencies":{"typescript":"5.7.3"}}',
        encoding="utf-8",
    )

    facts = engine.detected_stack_facts(tmp_path)

    assert "next 16.3.0" in facts
    assert "react 19.2.3" in facts
    assert "typescript 5.7.3" in facts
