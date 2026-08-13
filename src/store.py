import os
import tempfile
from pathlib import Path

from config import Config

# Default location, kept so the store is usable standalone (`python src/store.py`).
# Library callers pass their own directory to load_all() instead.
MEMORY_DIR = Config().memory_dir


def atomic_write_text(path, text, encoding="utf-8"):
    """Replace a text file atomically, so an interrupted UI worker cannot leave JSON
    or a memory file half-written.  The temporary file lives beside the target, which
    keeps ``os.replace`` atomic on Windows too."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding=encoding, newline="\n") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


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
    atomic_write_text(path, "\n".join(["---"] + out + ["---"] + lines[close + 1:]) + "\n")
    return True


def load_all(memory_dir=None):
    """Load every memory file under the memory tree (except .archive - forgotten-but-recoverable)."""
    memories = []
    for path in sorted(Path(memory_dir or MEMORY_DIR).rglob("*.md")):
        if ".archive" in path.parts:
            continue
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
