from store import atomic_write_text, parse_memory, patch_meta


def test_patch_meta_preserves_body_and_updates_frontmatter(tmp_path):
    path = tmp_path / "memory.md"
    atomic_write_text(path, "---\nid: test\nlinks: [one]\n---\nA body: with punctuation.\n")
    assert patch_meta(path, {"activation": 75}, remove=("links",))
    meta, body = parse_memory(path)
    assert meta == {"id": "test", "activation": "75"}
    assert body == "A body: with punctuation."


def test_atomic_write_replaces_the_complete_file(tmp_path):
    path = tmp_path / "state.json"
    atomic_write_text(path, '{"version": 1}')
    atomic_write_text(path, '{"version": 2}')
    assert path.read_text(encoding="utf-8") == '{"version": 2}'
