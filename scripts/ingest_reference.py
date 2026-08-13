"""Bulk-ingest a folder of .txt/.md documents into the `reference` branch.

The reference branch is BASE KNOWLEDGE: read-only world facts kept separate from the
personal brain (low importance, never part of the owner persona). Point this script at
any open corpus you have on disk - Wikipedia extracts, documentation dumps, textbook
chapters - and it chunks + registers them for hybrid retrieval.

Where to get open corpora (all freely licensed):
  * Wikipedia dumps / HuggingFace `wikimedia/wikipedia` (CC BY-SA) - start with a
    curated subset (Simple English, or the ~10k Vital Articles), NOT the full dump
  * Wikibooks/Wikiversity dumps, Project Gutenberg (public domain)
  * domain docs you already have locally (e.g. framework documentation)

SCALE WARNING: every memory costs an index-line embedding at load (disk-cached after
the first pass) and disk space. On a 4GB-GPU machine start with <= 1-2k documents,
measure retrieval + load time, then grow. This layer is meant to be curated, not to
mirror the internet.

Usage:
    python scripts/ingest_reference.py <folder> [--limit N] [--project <label>]
"""
import argparse
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from engine import MemoryEngine, chunk_text, slugify, MEMORY_DIR


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", help="folder containing .txt / .md documents")
    ap.add_argument("--limit", type=int, default=200, help="max documents this run (default 200)")
    ap.add_argument("--project", default="general", help="label grouping this corpus (default: general)")
    args = ap.parse_args()

    root = Path(args.folder)
    files = sorted([p for p in root.rglob("*") if p.suffix.lower() in (".txt", ".md") and p.is_file()])
    if not files:
        print(f"no .txt/.md files under {root}")
        return
    if len(files) > args.limit:
        print(f"capping at --limit {args.limit} of {len(files)} files (rerun to continue)")
        files = files[: args.limit]

    print("loading engine (embedder)...", flush=True)
    e = MemoryEngine()
    label = slugify(args.project)
    base = MEMORY_DIR / "reference" / label
    written = 0
    for i, f in enumerate(files, 1):
        try:
            text = f.read_text(encoding="utf-8", errors="ignore").strip()
        except OSError:
            continue
        if len(text) < 80:
            continue
        doc_id = f"ref-{label}-{slugify(f.stem)[:40]}"
        chunks = chunk_text(text, max_chars=700)
        title_line = text.split("\n", 1)[0].strip("# ").strip()[:90] or f.stem
        # parent card + chunk children, low importance: reference never outranks the personal brain by fiat
        e._write_memory(base / f"{doc_id}.md", doc_id, "reference", label, "source", 40,
                        f"# {title_line}\n(reference document: {f.name}, {len(chunks)} chunks)",
                        [f"{doc_id}-c{j + 1}:chunk" for j in range(len(chunks))], title_line)
        for j, ch in enumerate(chunks):
            cid = f"{doc_id}-c{j + 1}"
            e._write_memory(base / f"{cid}.md", cid, "reference", label, "chunk", 30,
                            ch, [f"{doc_id}:part-of"], ch[:60])
        written += 1
        if i % 25 == 0:
            print(f"  {i}/{len(files)} docs...", flush=True)
    print(f"wrote {written} documents into memory/reference/{label}/")
    print("re-embedding index (first load after ingest is the slow one)...", flush=True)
    e.reload_memories()
    print(f"done - corpus now {len(e.memories)} memories.")


if __name__ == "__main__":
    main()
