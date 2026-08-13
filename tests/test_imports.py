import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from app import extract_text_from_bytes


def test_extracts_text_uploads_without_writing_a_file():
    assert extract_text_from_bytes("notes.md", b"# Local RAG\nGrounded answers") == "# Local RAG\nGrounded answers"


def test_rejects_unsupported_uploaded_file_types():
    with pytest.raises(ValueError, match="Unsupported file type"):
        extract_text_from_bytes("archive.zip", b"not a document")
