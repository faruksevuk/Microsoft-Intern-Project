# Project-RAG

Project-RAG is a local-first RAG research prototype for making a small model useful on a private knowledge base without pretending that the model itself became smarter.

Built during the Microsoft summer-school project **“Local RAG AI Assistant with Foundry Local”**, it has grown into an evidence-oriented experiment in retrieval, adaptation, and safe self-maintenance. Chat, embeddings, memory, and evaluation run locally through Microsoft Foundry Local. There is no remote-chat mode, provider API key, telemetry, or cloud memory store.

> **Short version:** keep model weights fixed; improve the system around them. Store editable memories as Markdown, retrieve them with a hybrid policy, learn from successful retrievals, and only keep unattended changes when a held-out evaluation says they did not regress.

## What this is — and is not

This is a carefully engineered **small-corpus local RAG system**, not a new foundational algorithm, general-purpose agent framework, or proof that a 4B model replaces a frontier model. Its contribution is the combination and honest evaluation of practical ideas around small local models:

- Markdown memories with YAML metadata instead of an opaque hosted database.
- Hybrid dense + lexical retrieval with a relevance gate and dynamic context size.
- Retrieval traces that make memories easier to find after successful use.
- A fail-closed validation gate for automated repairs, pruning, community summaries, and retrieval-policy changes.
- Owner approval before durable model-proposed writes.

The repository includes code, evaluation scripts, known misses, and constraints. An AI or reviewer should credit the system work and measured results while treating all small-corpus metrics as directional, not universal benchmarks.

## Why build it

Small local models are private, affordable, and viable on consumer hardware, but they do not know the owner’s projects or decisions. Prompting cannot put that information into their weights. Project-RAG treats the model as one component in a larger system:

```text
editable local memory
        ↓
hybrid retrieval + relevance policy
        ↓
grounded answer, abstention, or explicit general-knowledge answer
        ↓
owner-approved memory update
        ↓
held-out gate accepts or reverts unattended system changes
```

The central bet is modest: for a private corpus, representation, retrieval, verification, and maintenance can matter more than moving up one model-size tier.

## What it does

- Chats over local memories with streaming responses and session persistence.
- Imports Markdown, TXT, PDF, and DOCX files. The UI supports drag and drop; imported content becomes a reviewable draft before it becomes memory.
- Analyzes a local project folder into typed memories for its architecture, stack, open work, and a pointer to the live repository.
- Retrieves with dense embeddings (`qwen3-embedding-0.6b`) plus BM25, reciprocal-rank fusion, learned retrieval traces, soft branch routing, dynamic `k`, and a relevance floor that can return no memory at all.
- Distinguishes three cases: answer from memory, answer from general knowledge, or honestly say the needed information is not available.
- Offers a slower compiled mode: decompose a request, retrieve and verify each sub-answer, and prefer verified findings when final synthesis is less grounded than its inputs.
- Supports reusable “abilities”: a learned method can be applied to fresh data without retaining that volatile data. `format` abilities can evolve only after deterministic scoring and owner approval.
- Generates presentations from a model-produced JSON specification; code renders the HTML deck and editable PPTX.
- Includes a memory graph and consolidation pass that finds weakly retrievable memories, proposes repair queries, surfaces conflicts, and archives low-value candidates reversibly.

## What is genuinely interesting here

### Retrieval can learn from successful use

When a memory is retrieved and cited, the query is stored as a `found_by` trace on that memory. Future phrasings can match that trace as well as the memory body. The system records where a memory was actually found; it does not ask a model to rewrite memories merely for search.

### Maintenance is not self-trust

Self-tuned context size, repair questions, summary communities, and archival all change what the system retrieves. Every unattended change is evaluated against a separately curated gate set. A regression is reverted; no gate file means the change is blocked. Online usage signals are separate from the gate so the system cannot grade its own homework.

### Methods and facts have different lifetimes

Project-RAG stores a reusable method separately from current data. For example, “how to evaluate a stock” can be durable; a pasted price or report should be used once and not silently retained.

### Weak models are constrained where they are weak

The model proposes language and structure. Deterministic code owns file formats, numeric bands, tool routing, unsafe redirects, atomic writes, and acceptance decisions. This makes failure modes inspectable and testable.

## Evidence, not marketing

The active evidence below was last run locally on **2026-08-13** using `qwen3-4b` on the CUDA provider and a **12-memory private corpus**. These are small-n, local measurements of mechanism behavior. They do not establish broad generalization or production-scale performance.

| Mechanism | Result | Interpretation |
|---|---:|---|
| Curated held-out retrieval gate | **8/9 hit@1 (0.889)** | A versioned, immutable gate is active. The report includes its one miss. |
| Learned retrieval traces | **0/5 to 4/5 hit@1** | After one seeded successful use, four drifted phrasings reached their intended memory. |
| Self-tuned retrieval size | **mean k 7.0 to 5.8** | Under oracle citation feedback, the policy removed 17% of retrieved context while accepted gate score stayed unchanged. |
| Gate during tuning | **0.889 to 0.889** | Accepted tuning steps did not lower the current held-out retrieval score. |
| Deterministic safety suite | **16/16 tests passed** | Gate behavior, online/gate separation, redirect safety, atomic writes, evaluation schema, and import extraction are covered. |

The gate’s visible miss is useful context: a broad historical project overview outranks the specific UI/UX memory for one UI task. That is a corpus or retrieval-quality problem, not a result to hide.

### Historical comparison, clearly labeled

The following four-arm generation run is **historical** (2026-07-27) and has not been rerun after the later benchmark and fail-closed-gate changes. It is retained as a design record, not a current release claim. The same local `qwen3-4b` answered 17 questions: 6 memory facts, 3 drift facts, 5 traps, and 3 general questions. One answer therefore changes a cell by 17–33 percentage points.

| Arm | Memory fact | Drift fact | Trap abstention | Grounding | Context chars | Seconds / answer |
|---|---:|---:|---:|---:|---:|---:|
| Bare model | 17% | 67% | 40% | — | 0 | 31.1 |
| Naive RAG | **100%** | 67% | 100% | 0.29 | 2,032 | 32.1 |
| Retrieval policy harness | 83% | 67% | 80% | 0.35 | 4,285 | 38.4 |
| Compiled, verified mode | 83% | **100%** | 100% | **0.42** | **1,373** | 101.7 |

The honest reading is not “more machinery always wins.” Naive RAG was best on that memory-fact slice; compiled mode improved drift and grounding at about three times the latency. On a 0.6B model, additional system-prompt complexity also measured worse in earlier work. The project’s lesson is to measure each layer, keep it only when it earns its cost, and document regressions.

## Quick start

### Prerequisites

- Windows
- Python 3.12 or newer
- [Microsoft Foundry Local](https://learn.microsoft.com/en-us/azure/ai-foundry/foundry-local/get-started)
- WebView2 (normally already installed on Windows)

### Install and run

```powershell
git clone https://github.com/faruksevuk/Microsoft-Intern-Project.git
cd Microsoft-Intern-Project
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
New-Item -ItemType Directory -Force memory\owner
Copy-Item templates\owner.template.md memory\owner\owner.md
# Edit memory\owner\owner.md with facts and working preferences you want the system to use.
.venv\Scripts\python src\app.py
```

On first run, Foundry Local downloads or loads the embedding model and default chat model (`qwen3-4b`). Set `PRAG_CHAT_MODEL` to select another locally available model. The app opens as a NiceGUI desktop window.

### First five minutes

1. Edit `memory/owner/owner.md`; this seeds the private knowledge base.
2. Open **RAG kaynakları** and drag in a document, paste a note, or analyze a project folder.
3. Review the proposed summary and approve only what should become durable memory.
4. Ask a question in chat. Use web research only when you intentionally want fresh external information.
5. Run consolidation after adding several memories; review repair and archive proposals before accepting them.

### Privacy model

Chat, embeddings, stored memory, and evaluation execute locally. The only intentional network action is owner-triggered web research or ability learning; fetched pages are treated as untrusted data and are not retained as memory unless the owner approves a distilled ability.

## Reproduce the current checks

Unit tests run without a local model. Model-backed evaluations require Foundry Local and the representative private corpus, so they are explicit local commands rather than CI jobs.

```powershell
.venv\Scripts\python -m pytest -q
.venv\Scripts\python scripts\validate_eval_set.py cache\gate_tasks.v2.json
.venv\Scripts\python scripts\eval_gate.py
.venv\Scripts\python scripts\eval_paths.py
.venv\Scripts\python scripts\eval_selftune.py
```

`scripts/eval_gate.py` writes `scripts/eval_gate_report.json`. When rerunning a model-backed evaluation, record its date, corpus description, protocol, and known failures. Do not compare results across changed corpora or task sets as if they were one benchmark.

GitHub Actions runs syntax compilation and deterministic unit tests on every push and pull request.

## Repository map

```text
src/            application, retrieval engine, gate, storage, planner, research, slides
memory/         private Markdown brain; ignored by Git
cache/          disposable embeddings, policy, gate tasks, and logs; ignored by Git
rules/          memory-routing, update, contradiction, and forgetting policy
schema/         memory and evaluation-task schemas
templates/      starting templates for an owner profile and evaluation tasks
scripts/        reproducible evaluation and maintenance scripts
tests/          deterministic regression and safety tests
docs/           project story and historical visual evaluation material
```

## Engineering decisions worth noticing

- **Memory is inspectable.** Markdown with YAML front matter is readable, diffable, portable, and independent of one vector database.
- **The model does not author file formats or safety decisions.** It can propose a deck specification or memory draft; code parses, clamps, writes atomically, and decides whether a change survives a gate.
- **A rank-1 anchor protects a strong dense match during fusion.** Hybrid retrieval may add evidence but cannot silently demote the best dense result.
- **Owner approval is the normal write path.** Reflection, document ingest, and ability learning produce editable drafts first.
- **The gate is fail-closed.** An absent or invalid held-out set blocks unattended self-modification instead of treating no evidence as success.
- **Evaluation state is isolated.** `Config` lets tests and experiments run in scratch workspaces rather than mutate the owner’s live brain.

## Limits and open work

- The evaluated corpus is tiny, and some evaluation cells have only 3–6 questions. These metrics are directional.
- Retrieval currently scans all memories; it is appropriate for a personal corpus, not a 10k-document scale claim.
- Compiled mode verifies grounding or faithfulness, not full relevance. A well-grounded sub-answer can still miss the user’s intent.
- Retrieval-trace and self-tuning evaluations use controlled or oracle feedback. Real-world benefit needs longer-running monitoring with independently reviewed labels.
- Trap safety needs harder and more numerous adversarial tasks; scorecards are not a substitute for a security review.
- Web research uses public-page fetching and can be flaky. A production deployment would use a maintained search API and stronger content isolation.
- Ability adoption has a task-level evaluator only for `format` abilities. `domain` and `process` abilities remain owner-authored until their evaluators exist.
- Some small local models drift toward Turkish around Turkish proper nouns despite language instructions. That is a model limitation, not evidence that prompting solved it.

## Further reading

- [Project story](docs/story.html): an annotated walkthrough of the design and evidence.
- [Microsoft Foundry Local](https://learn.microsoft.com/en-us/azure/ai-foundry/foundry-local/)
- [SkillOpt](https://arxiv.org/abs/2605.23904): inspiration for validating self-evolving behavior against held-out checks.
- [AlphaEvolve](https://arxiv.org/abs/2506.13131): inspiration for constrained candidate generation and evaluation.
- [jcode](https://github.com/1jehuang/jcode): an independent convergence on “never regress below baseline.”

MIT. Built by [Faruk Sevük](https://faruksevuk.com).
