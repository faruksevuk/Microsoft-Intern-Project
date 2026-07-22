# Memory constitution

Rules the system follows when reading and writing memory. Generic — anyone can adopt these.

## Capture
Store only what is important, reusable, or identity/decision-relevant. Skip the ephemeral.

## Route
- identity / preferences → `owner`
- project-specific facts → `sources/<project>`
- general, transferable lessons → `learnings`
- conversation outcomes → `past-chats`
- how the system itself values/keeps memories → `rules` (see `memory/rules/scoring.md`; the engine reads it)

## Store as text vs pointer
- Stable / distilled (facts, preferences, lessons, decisions) → store the text.
- Volatile (code, active repo, live data) → store a pointer; fetch fresh when needed.

## Update vs create
If a memory on the same topic exists, update it. Never create duplicates.

## Contradiction
If new information conflicts with an existing memory, reconcile: keep the truer/newer, note the change in `source`. Never keep both blindly.

## Importance & forgetting
- `importance_base` is a permanent floor: high for identity/milestones (never pruned), low for routine.
- `activation` decays over time, rises on use.
- Prune only low-base, long-unused, low-activation memories. Never touch high-base.

## Provenance
Every memory records where it came from and when.

## Compression
Memories are distilled, not raw dumps. Short, high-signal, English. This is a hard rule, not a preference — it is how a weak local model stays sharp.

## Human in the loop
Model-judgment steps (self-edit, contradiction, distillation) propose; the owner approves or edits. Quality comes from the owner + deterministic code, not the model alone.
