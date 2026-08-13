"""Validate a corpus-specific benchmark before using it for project claims."""
import json
import sys
from pathlib import Path

ALLOWED_SPLITS = {"dev", "gate", "monitoring"}
ALLOWED_CATEGORIES = {"memory", "drift", "multihop", "trap", "general", "injection"}
REQUIRED = {"id", "split", "category", "q", "expect"}


def validate(tasks):
    errors, ids = [], set()
    if not isinstance(tasks, list):
        return ["benchmark root must be a JSON list"]
    for i, task in enumerate(tasks):
        where = f"task[{i}]"
        if not isinstance(task, dict):
            errors.append(f"{where}: must be an object")
            continue
        missing = REQUIRED - task.keys()
        if missing:
            errors.append(f"{where}: missing {', '.join(sorted(missing))}")
        task_id = task.get("id")
        if not isinstance(task_id, str) or not task_id.strip() or task_id in ids:
            errors.append(f"{where}: id must be a unique non-empty string")
        ids.add(task_id)
        if task.get("split") not in ALLOWED_SPLITS:
            errors.append(f"{where}: invalid split")
        if task.get("category") not in ALLOWED_CATEGORIES:
            errors.append(f"{where}: invalid category")
        if not isinstance(task.get("q"), str) or len(task.get("q", "").strip()) < 8:
            errors.append(f"{where}: query must be at least 8 characters")
        if not isinstance(task.get("expect"), list) or not all(isinstance(x, str) and x for x in task.get("expect", [])):
            errors.append(f"{where}: expect must be a list of non-empty memory IDs")
    return errors


def main(argv=None):
    argv = argv or sys.argv[1:]
    if len(argv) != 1:
        print("usage: validate_eval_set.py PATH")
        return 2
    try:
        tasks = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as ex:
        print(f"cannot read benchmark: {ex}")
        return 2
    errors = validate(tasks)
    if errors:
        print("INVALID benchmark")
        print("\n".join(f"- {e}" for e in errors))
        return 1
    by_split = {split: sum(t["split"] == split for t in tasks) for split in ALLOWED_SPLITS}
    print(f"VALID: {len(tasks)} tasks | " + " | ".join(f"{k}={v}" for k, v in sorted(by_split.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
