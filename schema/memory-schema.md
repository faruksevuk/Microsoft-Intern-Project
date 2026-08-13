# Memory file schema

Each memory is a markdown file: YAML frontmatter + a distilled body.

## Frontmatter
- `id` — unique slug
- `branch` — owner | sources | learnings | past-chats | rules | reference
- `project` — project name (sources/reference only; omit otherwise)
- `type` — fact | pointer | preference | lesson | episode | source | detail | chunk | rule
  | ability (a reusable method — procedural memory) | community (a generated group overview)
- `kind` — ability only: format | domain | process (what class of thing the method is)
- `applies_to` — ability only: the trigger text a request is matched against
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
A tiny always-loaded line per memory: `id | branch/project | summary | tags | asked: found_by`.
Index lines are embedded once and disk-cached (`cache/embeddings.json`); bodies are embedded
lazily and cached too, so unchanged text is never re-embedded.

## Retrieval as policy (`_select_memories` in `src/engine.py`)
Not a fixed top-k lookup — a decision with four stages:
1. **Soft route** — the query is compared to per-branch anchors; the winning branch (only if it
   clearly beats the runner-up) gets a small score boost. A boost, never a filter.
2. **Rank** — dense body-cosine (raised by any confident `found_by` trace) fused with BM25 over
   body+traces via Reciprocal Rank Fusion. The dense top-1 is anchored at rank 1, so fusion can
   never demote the best dense hit.
3. **Relevance gate** — if the best dense score is below the gate, retrieve NOTHING, so the
   answer comes from general knowledge or an honest "not in memory" instead of a weak match.
4. **Dynamic k** — beyond the top hit, keep memories clearing a learned floor (`rel_floor`,
   self-tuned from citation feedback within a clamped band), then pull in 1-hop graph
   neighbours at a reduced bar. k emerges: 1 for a pinpoint hit, many for a broad cluster, 0
   when nothing is relevant.

After ranking (so it can never change what was retrieved), each memory is compressed to the
body segments most relevant to the query; an identity question ("which/what X") always keeps
the segment carrying the concrete identifier.

The earlier ranker — `cosine × (0.85 + 0.3 × salience)` over the index top-M, depth-first by
subtree — is kept as `_select_twotier` for A/B only (`scripts/eval_ab.py`); it measured worse
on hit@1. Salience still governs decay/prune decisions below.

## Salience (deterministic — no model judgment)
- `salience = (importance_base + effective_activation) / 200`
- effective activation = `activation − 2 × idle_days` (anchor: `last_used`, else `updated`/`created`)
- on use: `activation += 15` (cap 100) and `last_used = today`, persisted to the file.

## Conflict guard
Before a new source is written, the closest same-branch memory is checked
(body similarity ≥ 0.78 ⇒ the owner chooses: update the existing memory or add as new).

## Self-governance (the four organs)
- Legislation: `rules/scoring.md` is a memory; the engine parses its bands/params at load.
  Reflection can propose amendments; the owner approves; git shows the constitution's evolution.
- Immunity: the hide-and-seek self-test probes every memory with its own body gist;
  lost nodes get owner-approved doc2query questions seeded into `found_by`.
  Health score history: `cache/health.log`.
- Execution: desire paths — cited-in-answer memories earn the query as a `found_by` trace
  (no trace for the top index hit; near-duplicate traces replace, not append).
- Judiciary: the validation gate (`src/gate.py`). Every unattended self-modification —
  repairs, the tuned `rel_floor`, community summaries, pruning — is applied, re-measured on
  curated held-out retrieval tasks, and REVERTED if the score dropped. Live usage is logged in a
  separate online-monitoring file and can never alter the gate set. Nothing the system does to
  itself is kept on faith; an absent curated set blocks unattended changes (fail-closed).

## Principle
Distilled > raw. Short, high-signal, English. Compression + index = performance.
