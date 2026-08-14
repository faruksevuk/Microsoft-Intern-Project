import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import engine
from engine import PROJECT_CATEGORIES, parse_project_analysis


def test_project_analysis_parser_keeps_all_structured_sections():
    response = """## tech stack
- Python and NiceGUI in src/app.py
## architecture
- Memory is stored as Markdown
## ui/ux patterns
- Drag and drop import
## design patterns
- Config isolates filesystem state
## idea
- Improve local RAG quality
## missings / todos
- Add larger-scale retrieval
"""

    result = parse_project_analysis(response)

    assert list(result) == PROJECT_CATEGORIES
    assert result["tech stack"] == "- Python and NiceGUI in src/app.py"
    assert result["missings / todos"] == "- Add larger-scale retrieval"


def test_project_analysis_parser_marks_missing_sections_explicitly():
    result = parse_project_analysis("## architecture\n- A single engine owns retrieval")

    assert result["architecture"] == "- A single engine owns retrieval"
    assert result["idea"] == "- not clear from the files"


def test_project_analysis_uses_one_model_completion(monkeypatch):
    instance = object.__new__(engine.MemoryEngine)
    calls = []
    monkeypatch.setattr(engine, "read_project", lambda path, max_chars: "=== src/app.py ===\nprint('ok')")

    def complete(messages):
        calls.append(messages)
        return "\n".join(f"## {cat}\n- grounded detail" for cat in PROJECT_CATEGORIES)

    instance._complete_safe = complete
    result = instance.analyze_project("D:/demo", "demo")

    assert len(calls) == 1
    assert result["categories"]["architecture"] == "- grounded detail"
