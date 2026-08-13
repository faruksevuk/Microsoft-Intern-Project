from scripts.validate_eval_set import validate


def test_valid_benchmark_task():
    tasks = [{"id": "gate-1", "split": "gate", "category": "memory",
              "q": "Which memory contains the project model?", "expect": ["tech-stack"]}]
    assert validate(tasks) == []


def test_benchmark_rejects_duplicate_ids_and_unknown_split():
    tasks = [
        {"id": "same", "split": "gate", "category": "memory", "q": "A long enough query", "expect": ["a"]},
        {"id": "same", "split": "training", "category": "memory", "q": "Another long query", "expect": ["b"]},
    ]
    errors = validate(tasks)
    assert any("unique" in e for e in errors)
    assert any("split" in e for e in errors)
