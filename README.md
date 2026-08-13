# project-rag

A fully-local second brain that learns from being used. No cloud, no API keys, no telemetry — a ~1.5B–4B model running on a 4GB laptop GPU via [Microsoft Foundry Local](https://learn.microsoft.com/en-us/azure/ai-foundry/foundry-local/), made useful by system design instead of model size.

Built during the Microsoft summer school project *"Local RAG AI Assistant with Foundry Local"*, then taken considerably further.

> **Positioning:** a local-first RAG research prototype exploring safe adaptation around small models: learned retrieval traces, constrained policy tuning, and fail-closed validation gates. It adapts and evaluates existing ideas for this setting; it does not claim a new foundational algorithm.

**[The story](docs/story.html)** — an animated walkthrough of how the system works, what was borrowed from [SkillOpt](https://arxiv.org/abs/2605.23904)/[AlphaEvolve](https://arxiv.org/abs/2506.13131)/[jcode](https://github.com/1jehuang/jcode) and what changed, with per-claim proof links. Also available in-app in the information tab.

## the idea

Small local models are weak. You cannot fix that with prompting, and you cannot run a big model on a 4GB RTX 3050. So this project takes the other road: **hold the model constant, make everything around it learn.** Memory is markdown files with YAML frontmatter (readable, diffable, yours). Retrieval is a decision policy, not a lookup. And every mechanism that self-modifies must pass a validation gate before its change is kept — because a system that edits itself without one will eventually talk itself off a cliff (Microsoft's SkillOpt team [measured that cliff](https://arxiv.org/abs/2605.23904): −52.8 points in five nights, ungated).

Four things here learn from use, none of them touch model weights:

1. **desire paths** — a memory that gets found-and-cited earns the query as a `found_by` trace; drifted future phrasings then find it. Latest local run: drift-query hit@1 **0/5 → 4/5** after one seeded use.
2. **self-tuning retrieval** — how many memories to retrieve (`rel_floor`) is learned from citation feedback, band-clamped, evidence-gated. Latest local run: average k **7.0 → 5.8**; each accepted step preserved the curated gate score.
3. **consolidation ("sleep")** — the brain probes each memory with its own content; unfindable ones get doc2query repair questions, contradictions get flagged. Measured: findability health **50% → 80%** in one pass.
4. **abilities** — reusable *methods* (procedural memory), typed `format` / `domain` / `process`. Learned once from research, then applied to fresh volatile data. The stock price is never stored; *how to analyze a stock* is. Abilities also **evolve**, AlphaEvolve-style: diverse variants are generated, scored by a deterministic evaluator (first-try parse + structure + grounding), and the winner is adopted only with owner approval — losers are archived and never re-proposed. Measured, generation 1: **0.667 → 0.800**.

All of it sits behind a **held-out validation gate** (`src/gate.py`): every unattended self-modification is re-measured on curated tasks and rolled back if the score drops. If no curated gate exists, it is blocked (fail-closed), not accepted without evidence.

## what it does

- **chat grounded in your memory**, streaming, session persistence, verbatim working memory (retrieval of stored turns, not lossy summaries)
- **compiled ("deep") mode**: the request is decomposed, every step is answered from its own retrieval and must pass a grounding check before the next step may use it, a failing step is split one level deeper, and the final integration is itself verified — if the composed answer is less grounded than its own inputs, code renders the verified findings instead. Toggle it per message; it costs ~3× latency and buys the numbers in the table below.
- **hybrid retrieval**: dense (qwen3-embedding-0.6b) + BM25 over bodies *and* learned traces, RRF-fused, rank-1 anchored so fusion can never demote the best dense hit
- **retrieval as policy**: relevance gate (retrieve *nothing* when nothing is relevant — three-way abstention: memory / general knowledge / honest "I don't have that"), soft branch routing (a boost, never a filter), dynamic k
- **structured project ingest**: point it at a repo, it crawls tree+manifests+source and writes typed memories (tech stack, architecture, missings, a live repo pointer) as a `part-of` hierarchy
- **web research**: answer from a fetched source with citation (volatile, not persisted) or distill a reusable *ability* (persisted, owner-approved)
- **slide generation**: "make me a deck about X" → triage → plan → retrieve/research → the model emits a small JSON spec → *code* renders an animated self-contained HTML deck + editable .pptx. The model never touches a file format; that is why the output looks good.
- **the brain view**: force-graph of the memory tree, node click to edit/delete, one-click consolidation

## current evidence

The following were re-run locally on **2026-08-13** with `qwen3-4b` on the CUDA provider and the current 12-memory private corpus. They are small-corpus results, so they show mechanism behaviour rather than broad generalization.

| mechanism | current result | what it establishes |
|---|---:|---|
| curated validation gate | **8/9 hit@1 (0.889)** | a real, immutable gate is active; it is no longer an auto-seeded proxy |
| desire paths | **0/5 → 4/5 hit@1** | one use can make four formerly-unfindable drifted phrasings retrieve their intended memory |
| self-tuning retrieval | **k 7.0 → 5.8** | the controller removes 17% of retrieved context under oracle citation feedback |
| gate through tuning | **0.889 → 0.889** at every accepted step | tuning did not reduce curated retrieval hit@1 |
| deterministic safety suite | **14/14 passed** | fail-closed gate, online/gate separation, redirect safety, atomic writes, and eval schema are covered |

`scripts/eval_gate.py`, `scripts/eval_paths.py`, and `scripts/eval_selftune.py` reproduce the first four rows. The gate report intentionally exposes its one miss: the broad historical `foundry-rag` overview outranks the specific UI/UX memory for one UI task. That is a memory-quality issue to fix, not a metric to hide.

### historical wrapper comparison

The broader four-arm generation harness has not yet been re-run after the fail-closed gate and benchmark changes. Its last local run is retained below as **historical**, not a current release claim. Re-run `scripts/eval_harness.py` before citing it externally.

**Last run: 2026-07-27. Same model, four wrappers** (`scripts/eval_harness.py`, qwen3-4b on GPU, n=17 questions —
6 memory / 3 drift / 5 trap / 3 general, so one answer moves a cell by 17–33 points):

| arm | memory fact | drift fact | trap abstain | general | grounding | ctx chars | sec/ans |
|---|---|---|---|---|---|---|---|
| A bare model | 17% | 67% | 40% | 100% | — | 0 | 31.1 |
| B naive RAG (flat cosine top-4) | **100%** | 67% | 100% | 100% | 0.29 | 2032 | 32.1 |
| C harness (retrieval as policy) | 83% | 67% | 80% | 100% | 0.35 | 4285 | 38.4 |
| D compiled (verified step-program) | 83% | **100%** | 100% | 100% | **0.42** | **1373** | 101.7 |

The bare model answered a trap question — "the owner's finishing time in the 2019 Istanbul
Marathon" — with a confident **2:17:06**. The same model inside the harness says it isn't in
memory. Nothing about the weights changed.

**Historical model-size experiment** (`docs/eval-ladder.svg`, same suite across the qwen3 family; re-run required before external use)

| | 0.6b | 1.7b | 4b |
|---|---|---|---|
| bare, memory facts | 33% | 33% | 33% |
| harness, memory facts | 50% | 67% | **100%** |
| harness, sec/ans | 3.0 | 5.6 | 31.8 |

Bare accuracy on personal facts is **flat across a 7× parameter range** — your life is not in the
weights, so scale cannot buy it. Meanwhile 0.6b + harness (50%, 3.0s) beats 4b bare (33%, ~18s).
Structure is worth more than a model-size step *and* an order of magnitude faster.

Two honest limits in that table: the harness's trap resistance is *prompt obedience*, and it only
locks in at 4b (40% → 40% → 100%) — while compiled mode's checks are *code*, so they hold a 60%
floor at sizes where prompts fail. And at 0.6b the naive arm beats the harness on memory facts
(67% vs 50%): the big persona-and-rules prompt overwhelms a 0.6B model. Scaffolding complexity is
itself a capability cost.

Other historical mechanism runs (older corpus/configuration; re-run before external use):

| thing | baseline | this system |
|---|---|---|
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

First run downloads the models (qwen3-embedding-0.6b + qwen3-4b by default; override with `PRAG_CHAT_MODEL`). The app opens as a native window (NiceGUI + WebView2). Your brain starts empty — ingest a project, save a chat reflection, teach it an ability.

### your GPU is probably idle — this fixes it

Foundry Local's Python SDK serves a **CPU-only catalog** until GPU execution providers are
registered, and registration does **not persist across processes**. So every model resolves to a
`generic-cpu` build, silently, forever. Even once EPs are registered, the default variant is still
the CPU one — the GPU build has to be selected explicitly.

The engine now does both at startup (`_ensure_gpu_eps` + `_select_device_variant`), which on a 4GB
RTX 3050 took inference from ~10 to **~44 tok/s**. Costs ~5s per launch once the EP binaries are
cached; set `PRAG_DEVICE=cpu` to opt out. Note that `phi-4-mini` has **no CUDA build** in this
catalog — models that do include qwen3-4b / qwen3-1.7b / qwen3-0.6b / phi-4-mini-reasoning.

Your data never leaves the machine. The only network calls are the ones *you* trigger (web research / ability learning), and fetched pages are treated strictly as data, never as instructions.

### local-only by design

Chat, embeddings, memory and evaluation all run through Foundry Local. Project-RAG has no remote chat/API mode and never stores a provider API key.

The only network calls are owner-triggered web research; fetched pages are treated as untrusted data.

## repo layout

```
src/
  engine.py     the core: memory, hybrid retrieval policy, salience, reflection,
                desire paths, self-test, consolidation, abilities, validation gate wiring
  config.py     every filesystem location in one injectable object — pass one to run
                an isolated brain (evals, tests) or embed the engine in your own app
  gate.py       immutable held-out validation gate (accept/reject/rollback for self-edits)
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

## evaluation protocol

- Keep `cache/gate_tasks.v2.json` as a manually curated, versioned held-out set. Copy
  `templates/gate_tasks.example.json` as a starting shape, then replace its example IDs.
  The engine never seeds or modifies this file. Until it exists, unattended self-modification is
  **blocked** (fail-closed), never silently accepted.
- Successful real-use queries are recorded separately in `cache/online_monitoring_tasks.json`.
  They are useful operational evidence, never a validation score.
- `tests/` covers the deterministic safety core and `.github/workflows/ci.yml` runs syntax and
  unit checks on every push. Model-backed harnesses remain explicit local runs because they
  require Foundry models and a representative private corpus.

Run the current evidence suite locally:

```powershell
.venv\Scripts\python -m pytest -q
.venv\Scripts\python scripts\validate_eval_set.py cache\gate_tasks.v2.json
.venv\Scripts\python scripts\eval_gate.py
.venv\Scripts\python scripts\eval_paths.py
.venv\Scripts\python scripts\eval_selftune.py
```

## limitations, honestly

- the corpus is small (12 memories) and n per eval cell is 3–6; every number is directional, and one answer moves a cell by up to 33 points
- retrieval is a full scan over all memories each query (fine at this size, wrong at 10k) — the index needs a real vector store before scale claims
- small local models drift to Turkish on queries containing Turkish proper nouns despite a 3-level language directive — model limit, not fixable by prompting
- compiled mode verifies *faithfulness*, not *relevance*: a step can be grounded in memory and still not answer its sub-question (measured — it answered "name two projects" with an unrelated but genuinely-stored fact)
- audience-appropriate pedagogical writing (explain to a 6-year-old) is beyond a 4B model
- web search is scraping (DuckDuckGo) and inherently flaky; a real search API would harden it
- ability adoption re-runs its deterministic task-level score and rejects regressions; this is
  currently available only for `format` abilities. Domain/process abilities remain owner-authored
  until each has a task-level evaluator; expand those suites as new ability kinds land
- the eval scorer turned out to be the weakest link: four times in one session it punished a correct answer (a valid paraphrase, three validly-worded refusals). The trap metric now detects **fabrication** — per-question patterns for what an invented claim looks like — instead of hunting for abstention phrases, so honesty is measured rather than wording. Keyword matching on the fact questions stays a known weak spot
- with the corrected scorer every arm scores 100% trap-safe on the current 12-memory corpus; trap resistance needs harder and more numerous traps before it discriminates between arms again

## references

- SkillOpt: executive strategy for self-evolving agent skills — [arXiv:2605.23904](https://arxiv.org/abs/2605.23904) (the validation-gate evidence)
- lost in the middle, verbatim-beats-summaries line of work that motivated the working memory design
- [Foundry Local docs](https://learn.microsoft.com/en-us/azure/ai-foundry/foundry-local/)

MIT. Built by [Faruk Sevük](https://faruksevuk.com).
