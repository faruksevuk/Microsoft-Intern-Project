# Memory constitution

Rules the system follows when reading and writing memory. Generic — anyone can adopt these.

## Capture
Store only what is important, reusable, or identity/decision-relevant. Skip the ephemeral.

## Route
- identity / preferences → `owner`
- project-specific facts → `sources/<project>`
- general, transferable lessons → `learnings` (reusable methods live here too, as `type: ability`)
- conversation outcomes → `past-chats`
- how the system itself values/keeps memories → `rules` (see `memory/rules/scoring.md`; the engine reads it)
- impersonal world knowledge (encyclopedia, docs) → `reference`, kept deliberately low-importance
  so borrowed facts never outrank what the owner actually told the system

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

## Knowledge vs findability
A memory's body is knowledge and stays pure — it is never edited to make retrieval easier.
Findability learns separately: the queries a memory was genuinely found-and-cited by are kept
on its index line (`found_by`), so later paraphrases reach it. Learning where things are must
never change what they say.

## Skills are memories too
A method that works is worth keeping the way a fact is: stored as `type: ability`, typed by
`kind` (format / domain / process), applied to fresh data on demand. The method persists; the
data it was applied to does not.

## Nothing self-modifying is kept unmeasured
Any change the system makes to itself without the owner watching — repairs, a tuned retrieval
floor, generated summaries, pruning — must be applied, re-measured against held-out tasks, and
rolled back if the score dropped. A system that edits itself without a gate will eventually
talk itself off a cliff. Improvement is allowed to fail; it is not allowed to be assumed.

The held-out gate set is curated and immutable during normal use. Real successful queries may be
logged for online monitoring, but they must never become gate tasks: a system cannot grade itself
on questions it learned from. If there is no curated gate set, unattended self-modification is
blocked rather than accepted without evidence.

## Human in the loop
Model-judgment steps (self-edit, contradiction, distillation) propose; the owner approves or edits. Quality comes from the owner + deterministic code, not the model alone.
