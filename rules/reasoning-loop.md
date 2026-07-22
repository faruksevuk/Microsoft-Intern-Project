# Reasoning & confirmation loop

How the system reasons, and when it must confirm with the owner. Pairs with `constitution.md`.

## Reasoning protocol
On important or uncertain decisions, reason before concluding:
1. State the goal.
2. List the relevant memories by id.
3. Reason step by step.
4. Propose a decision.

Skip this for trivial retrieval — reasoning has a latency cost; spend it where it pays.

## When to ask the owner (deterministic triggers, not the model's self-assessment)
A small model cannot judge its own uncertainty reliably. Ask the owner only when a deterministic trigger fires:
- a write to a high-`importance_base` memory (owner, key decisions)
- a detected contradiction with an existing memory
- low retrieval similarity (no confident match = uncertain)
- an irreversible or important-tagged action

The owner sets the thresholds.

## Confirm, learn, verify the distillation
When a trigger fires, do not act silently:
1. Present the reasoning AND the inference about the owner: "I reasoned X because Y; based on what I know about you, Z — is that right?"
2. Owner confirms or corrects the decision.
3. The model distills the outcome and SHOWS the draft: "Here is what I'll remember: […]."
4. Owner confirms or corrects the distillation. (The owner may not articulate their own judgment well; the draft is a mirror that is easier to react to.)
5. Only then write it — to `owner`/preferences for judgment, else the relevant branch.

These verified memories compound: future decisions improve and the system asks less over time.
