# Memory file schema

Each memory is a markdown file: YAML frontmatter + a distilled body.

## Frontmatter
- `id` — unique slug
- `branch` — owner | sources | learnings | past-chats | rules
- `project` — project name (sources only; omit otherwise)
- `type` — fact | pointer | preference | lesson | episode | source | detail | chunk | rule
- `importance_base` — 0-100; proposed by the model within the band from `rules/scoring.md`, owner-approved, clamped in code
- `activation` — 0-100, dynamic; decays over time, rises on use
- `last_used` — date of last retrieval (the decay anchor; written by the engine)
- `found_by` — desire paths: queries/questions this memory was truly found-and-used by; index-line only, never the body
- `tags` — [keyword, ...] cheap filter layer
- `summary` — one line: "when is this relevant" (used in the index)
- `links` — [other-id, ...] associative links
- `source` — provenance (where/when it came from)
- `created` / `updated` — dates

## Body
Distilled, high-signal content. For `type: pointer`, a path/URL to fetch fresh instead of stored text.

## Index (the performance core)
A tiny always-loaded line per memory: `id | branch/project | summary | tags`.
Recall is two-tier, as implemented in `src/engine.py`:
1. Embed only the index lines (disk-cached in `cache/embeddings.json`); rank them against the query.
2. Embed only the top candidates' bodies (also cached, lazily) and re-score as
   `cosine × (0.85 + 0.3 × salience)`, then pick depth-first (best subtree) + breadth.
The model never reads everything; unchanged text is never re-embedded.

## Salience (deterministic — no model judgment)
- `salience = (importance_base + effective_activation) / 200`
- effective activation = `activation − 2 × idle_days` (anchor: `last_used`, else `updated`/`created`)
- on use: `activation += 15` (cap 100) and `last_used = today`, persisted to the file.

## Conflict guard
Before a new source is written, the closest same-branch memory is checked
(body similarity ≥ 0.78 ⇒ the owner chooses: update the existing memory or add as new).

## Self-governance (the three organs)
- Legislation: `rules/scoring.md` is a memory; the engine parses its bands/params at load.
  Reflection can propose amendments; the owner approves; git shows the constitution's evolution.
- Immunity: the hide-and-seek self-test probes every memory with its own body gist;
  lost nodes get owner-approved doc2query questions seeded into `found_by`.
  Health score history: `cache/health.log`.
- Execution: desire paths — cited-in-answer memories earn the query as a `found_by` trace
  (no trace for the top index hit; near-duplicate traces replace, not append).

## Principle
Distilled > raw. Short, high-signal, English. Compression + index = performance.
