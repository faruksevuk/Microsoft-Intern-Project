import json

import gate


def test_gate_rejects_a_regression():
    result = gate.decide("retrieval", 0.8, 0.7)
    assert result.action == "reject"
    assert not result


def test_gate_accepts_an_equal_score():
    result = gate.decide("retrieval", 0.8, 0.8)
    assert result.action == "accept"
    assert result


def test_gate_blocked_result_is_not_truthy():
    result = gate.GateResult("blocked", "repair", -1, -1)
    assert not result
    assert "BLOCKED" in result.summary()


def test_missing_gate_file_is_not_auto_seeded(tmp_path):
    path = tmp_path / "gate_tasks.json"
    memories = [{"meta": {"id": "m1", "summary": "A sufficiently long memory summary"}}]
    assert gate.load_tasks(path, memories) == []
    assert not path.exists()


def test_gate_loads_only_valid_curated_tasks(tmp_path):
    path = tmp_path / "gate_tasks.json"
    path.write_text(json.dumps([{"q": "where is the project", "expect": ["pointer"]}]), encoding="utf-8")
    assert gate.load_tasks(path) == [{"q": "where is the project", "expect": ["pointer"]}]
