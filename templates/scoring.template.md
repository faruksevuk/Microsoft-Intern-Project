---
id: rule-scoring
branch: rules
type: rule
importance_base: 95
activation: 100
tags: [rules, scoring, governance, paths]
summary: How memories are valued - importance bands, judgment questions, path thresholds. The engine reads this file.
links: []
source: co-designed 2026-07-17
created: 2026-07-17
updated: 2026-07-17
---
# Scoring constitution

The engine parses the `band:` and `param:` lines below at load time - editing this file changes behavior.
Everything else is guidance for the model and the owner. Amendments are appended at the bottom, dated.

## Judgment questions (the model answers these when proposing a score)
- Is it identity- or decision-relevant? Higher.
- Would losing it hurt in 3 months? Higher.
- Can it be regenerated from a source file or repo? Lower.
- Do other memories link to it? Higher.

## Scoring bands (machine-read)
- band: rule | floor: 85 | cap: 100 | default: 90
- band: preference | floor: 60 | cap: 95 | default: 75
- band: fact | floor: 45 | cap: 85 | default: 60
- band: lesson | floor: 50 | cap: 80 | default: 60
- band: source | floor: 55 | cap: 80 | default: 65
- band: detail | floor: 40 | cap: 70 | default: 50
- band: pointer | floor: 45 | cap: 65 | default: 55
- band: episode | floor: 35 | cap: 65 | default: 50
- band: chunk | floor: 25 | cap: 50 | default: 40

## Path thresholds (machine-read)
- param: citation_sim | value: 0.60
- param: trace_dedup_sim | value: 0.90
- param: max_traces | value: 3
- param: selftest_topk | value: 3

## Branch overrides (enforced in code)
Owner-branch memories never score below 90; rules-branch never below 85.

## Desire-path rules
- A trace is earned only when the memory was actually cited by the answer (citation_sim).
- No paving highways: the top index hit for a query earns no trace.
- A new trace that closely matches an existing one replaces it (trace_dedup_sim); diversity is kept.
- Traces live only in the index line, never in the body. Knowledge stays pure; findability learns.

## Amendments
- none yet
