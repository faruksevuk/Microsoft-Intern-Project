# Benchmark protocol

Keep private benchmark files outside Git (for example in `memory/evals/`) and validate them with:

```powershell
.venv\Scripts\python scripts\validate_eval_set.py memory\evals\benchmark.json
```

Target at least 100 tasks before making general performance claims. Balance categories and reserve
at least 20% for `gate`. Copy only its `gate` rows to `cache/gate_tasks.v2.json`; the task file is
corpus-specific because expected memory IDs are private.
Use `templates/eval_tasks.example.json` only as a structural example.
