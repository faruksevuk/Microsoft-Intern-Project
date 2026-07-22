from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MEMORY_DIR = ROOT / "memory"


def parse_memory(path):
    """Split a memory file into (frontmatter dict, body). Stdlib only.

    The closing delimiter is matched only on a line that is exactly '---', so a
    literal '---' inside a value (e.g. a slug or summary) never truncates it.
    """
    text = path.read_text(encoding="utf-8")
    meta, body = {}, text
    if text.startswith("---"):
        lines = text.splitlines()
        close = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
        if close is not None:
            body = "\n".join(lines[close + 1:])
            for line in lines[1:close]:
                if ":" not in line:
                    continue
                key, val = (s.strip() for s in line.split(":", 1))
                if val.startswith("[") and val.endswith("]"):
                    val = [v.strip() for v in val[1:-1].split(",") if v.strip()]
                meta[key] = val
    return meta, body.strip()


def _fmt_meta(val):
    if isinstance(val, list):
        return "[" + ", ".join(str(v) for v in val) + "]"
    return str(val)


def patch_meta(path, updates, remove=()):
    """Update/insert (or remove) frontmatter keys in place; the body is untouched.

    Used for dynamic fields (activation, last_used, links, found_by, updated) so
    salience/path bookkeeping never risks mangling a memory's content.
    """
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return False
    lines = text.splitlines()
    close = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if close is None:
        return False
    out, done = [], set()
    for line in lines[1:close]:
        key = line.split(":", 1)[0].strip() if ":" in line else None
        if key in remove:
            continue
        if key in updates:
            out.append(f"{key}: {_fmt_meta(updates[key])}")
            done.add(key)
        else:
            out.append(line)
    out += [f"{key}: {_fmt_meta(val)}" for key, val in updates.items() if key not in done]
    path.write_text("\n".join(["---"] + out + ["---"] + lines[close + 1:]) + "\n", encoding="utf-8")
    return True


def load_all():
    """Load every memory file under memory/."""
    memories = []
    for path in sorted(MEMORY_DIR.rglob("*.md")):
        meta, body = parse_memory(path)
        memories.append({"path": path, "meta": meta, "body": body})
    return memories


def build_index(memories):
    """The tiny always-loaded layer: one line per memory."""
    lines = []
    for m in memories:
        meta = m["meta"]
        lines.append(
            f"- {meta.get('id', '?')} | {meta.get('branch', '?')} | "
            f"imp {meta.get('importance_base', '?')} | {meta.get('summary', '')}"
        )
    return "\n".join(lines)


def main():
    memories = load_all()
    print(f"Loaded {len(memories)} memories from {MEMORY_DIR}\n")
    print("INDEX (always loaded):")
    print(build_index(memories))


if __name__ == "__main__":
    main()
