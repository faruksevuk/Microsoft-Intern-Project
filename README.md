# project-rag

A fully-local second brain that learns from being used. No cloud, no API keys, no telemetry — a ~1.5B–4B model running on a 4GB laptop GPU via [Microsoft Foundry Local](https://learn.microsoft.com/en-us/azure/ai-foundry/foundry-local/), made useful by system design instead of model size.

Built during the Microsoft summer school project *"Local RAG AI Assistant with Foundry Local"*, then taken considerably further.

## the idea

Small local models are weak. You cannot fix that with prompting, and you cannot run a big model on a 4GB RTX 3050. So this project takes the other road: **hold the model constant, make everything around it learn.** Memory is markdown files with YAML frontmatter (readable, diffable, yours). Retrieval is a decision policy, not a lookup. And every mechanism that self-modifies must pass a validation gate before its change is kept — because a system that edits itself without one will eventually talk itself off a cliff (Microsoft's SkillOpt team [measured that cliff](https://arxiv.org/abs/2605.23904): −52.8 points in five nights, ungated).

Four things here learn from use, none of them touch model weights:

1. **desire paths** — a memory that gets found-and-cited earns the query as a `found_by` trace; drifted future phrasings then find it. Measured: drift-query hit@1 went **0/5 → 4/5** after single use.
2. **self-tuning retrieval** — how many memories to retrieve (`rel_floor`) is learned from citation feedback, band-clamped, evidence-gated. Measured: over-retrieval k 7.0 → 3.8 with hit@1 flat.
3. **consolidation ("sleep")** — the brain probes each memory with its own content; unfindable ones get doc2query repair questions, contradictions get flagged. Measured: findability health **50% → 80%** in one pass.
4. **abilities** — reusable *methods* (procedural memory), typed `format` / `domain` / `process`. Learned once from research, then applied to fresh volatile data. The stock price is never stored; *how to analyze a stock* is.

## what it does

- **chat grounded in your memory**, streaming, session persistence, verbatim working memory (retrieval of stored turns, not lossy summaries)
- **hybrid retrieval**: dense (qwen3-embedding-0.6b) + BM25 over bodies *and* learned traces, RRF-fused, rank-1 anchored so fusion can never demote the best dense hit
- **retrieval as policy**: relevance gate (retrieve *nothing* when nothing is relevant — three-way abstention: memory / general knowledge / honest "I don't have that"), soft branch routing (a boost, never a filter), dynamic k
- **structured project ingest**: point it at a repo, it crawls tree+manifests+source and writes typed memories (tech stack, architecture, missings, a live repo pointer) as a `part-of` hierarchy
- **web research**: answer from a fetched source with citation (volatile, not persisted) or distill a reusable *ability* (persisted, owner-approved)
- **slide generation**: "make me a deck about X" → triage → plan → retrieve/research → the model emits a small JSON spec → *code* renders an animated self-contained HTML deck + editable .pptx. The model never touches a file format; that is why the output looks good.
- **the brain view**: force-graph of the memory tree, node click to edit/delete, one-click consolidation

## numbers

All measured on the included eval scripts (`scripts/eval_*.py`), small corpus (11–70 memories), so treat them as directional:

| thing | baseline | this system |
|---|---|---|
| retrieval hit@1 (flat cosine) | 0.62 / 0.72 | 0.62 / 0.72 (parity — that axis was saturated) |
| retrieval hit@4 | 0.69 / 0.78 | **0.85 / 0.83** |
| context size | 100% | **46%** (query-focused compression, post-ranking so it cannot change hit@1) |
| drift-query findability | 2/7 forever | **6/7 after use** |
| findability health after one consolidation | — | **50% → 80%** |
| harmful self-edit (flattened ranking) | silently kept | **gate: REJECT (0.583→0.333), rolled back** |

The honest summary: where vanilla RAG is already strong (clean-corpus hit@1) we only tie. The wins are the axes a static RAG cannot have — learning from use, self-repair, refusing to degrade itself.

## quick start

You need Windows + [Foundry Local](https://learn.microsoft.com/en-us/azure/ai-foundry/foundry-local/get-started) installed, Python 3.12+.

```bash
git clone https://github.com/faruksevuk/Microsoft-Intern-Project.git
cd Microsoft-Intern-Project
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
mkdir memory\owner
copy templates\owner.template.md memory\owner\owner.md   # then edit: who are you, how do you work
.venv\Scripts\python src\app.py
```

First run downloads the models (qwen3-embedding-0.6b + phi-4-mini by default; override with `PRAG_CHAT_MODEL`). The app opens as a native window (NiceGUI + WebView2). Your brain starts empty — ingest a project, save a chat reflection, teach it an ability.

Your data never leaves the machine. The only network calls are the ones *you* trigger (web research / ability learning), and fetched pages are treated strictly as data, never as instructions.

## repo layout

```
src/
  engine.py     the core: memory, hybrid retrieval policy, salience, reflection,
                desire paths, self-test, consolidation, abilities, validation gate wiring
  gate.py       held-out validation gate (accept/reject/rollback for self-edits)
  planner.py    request decomposition: triage -> plan schema -> repair -> rule fallback
  slides.py     deck spec parser (tolerant) + animated HTML / pptx renderers
  research.py   web tool layer (DuckDuckGo/Wikipedia, untrusted-data-only)
  store.py      markdown+frontmatter memory store
  app.py        NiceGUI glassmorphism app (chat / brain graph / rag sources)
schema/         memory file schema, two-tier index, salience rules
rules/          the constitution: capture/route/update/contradiction/forgetting rules
templates/      owner template — start here
scripts/        eval harnesses (A/B retrieval, desire paths, self-tune, gate, jarvis)
memory/         YOUR brain — gitignored, never shared
```

## design rules that did the heavy lifting

- **the model never emits a number or a file format.** Importance scores are band-clamped code decisions; decks are JSON specs rendered by code. Weak models can't calibrate; don't ask them to.
- **rules decide what rules can decide.** Language detection, tool routing, retrieval gating — all deterministic. The model gets only the judgments structure can't make.
- **never regress below baseline.** The rank-1 anchor, the repair loops, the validation gate — every mechanism is allowed to help or do nothing, never to hurt. (Independently, both [jcode](https://github.com/1jehuang/jcode) and [SkillOpt](https://github.com/microsoft/SkillOpt) converged on the same rule.)
- **the owner approves writes.** Reflection, ingest, abilities — the model proposes, you adopt. Quality comes from the human + deterministic code, not the model alone.
- **measure, then keep or revert.** Several ideas in this repo were built, measured worse, and reverted (bullet-level ranking, aggressive audience simplification, a two-tier ranker). The eval scripts are in the repo; the failures are documented in the code comments.

## limitations, honestly

- the corpus is small; all numbers need re-validation at scale
- phi-4-mini drifts to Turkish on queries containing Turkish proper nouns despite a 3-level language directive — model limit, not fixable by prompting
- audience-appropriate pedagogical writing (explain to a 6-year-old) is beyond a 4B model
- web search is scraping (DuckDuckGo) and inherently flaky; a real search API would harden it
- ability edits are not yet gated (they need task-level scores, not retrieval scores)

## references

- SkillOpt: executive strategy for self-evolving agent skills — [arXiv:2605.23904](https://arxiv.org/abs/2605.23904) (the validation-gate evidence)
- lost in the middle, verbatim-beats-summaries line of work that motivated the working memory design
- [Foundry Local docs](https://learn.microsoft.com/en-us/azure/ai-foundry/foundry-local/)

MIT. Built by [Faruk Sevük](https://faruksevuk.com).
