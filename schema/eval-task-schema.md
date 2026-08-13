# Evaluation task schema

Evaluation is a versioned dataset, not a list embedded in an experiment script. Each task is a
JSON object with these fields:

- `id`: stable, unique identifier
- `split`: `dev`, `gate`, or `monitoring`
- `category`: `memory`, `drift`, `multihop`, `trap`, `general`, or `injection`
- `q`: user query
- `expect`: one or more expected memory IDs for retrieval tasks; empty for traps/general tasks
- `notes`: optional human scoring notes

Rules:

1. `gate` tasks are curated, versioned and never altered by the app at runtime.
2. `dev` tasks may guide tuning but must never be used for acceptance decisions.
3. `monitoring` tasks come from real use and measure production behaviour only.
4. Add a task only when its expected answer has been manually verified against the source memory.
5. Track the corpus snapshot, model alias, device and run timestamp next to every reported result.
