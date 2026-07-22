"""The decision layer: every request is decomposed before it is answered.

Split of responsibility (the only way this works on a weak local model):
  * RULES decide what rules can decide (format, language, whether memory sufficed)
  * the MODEL fills a small fixed PLAN schema (goal / audience / research / outline / tone)
  * ABILITIES of kind `format` supply the plan TEMPLATE for a task class
  * CODE validates, repairs, and executes - and falls back to a rule-built plan if the
    model's plan is unusable, so the system can never be worse than the fixed pipeline.
"""
import ast
import json
import re

PLAN_KEYS = ("goal", "audience", "format", "needs_research", "research_queries", "outline", "tone")
MAX_RESEARCH_QUERIES = 2
MAX_OUTLINE = 8


def parse_plan(raw):
    """Coerce the model's plan output into a dict, or None. Same tolerance ladder as
    the deck parser: fenced blocks, prose, single quotes, trailing commas, python dicts."""
    if isinstance(raw, dict):
        return _normalise(raw)
    text = (raw or "").strip()
    fence = re.search(r"```(?:json)?\s*(.+?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    blob = text[start:end + 1]
    no_commas = re.sub(r",\s*([}\]])", r"\1", blob)
    for attempt in (blob, no_commas, no_commas.replace("'", '"')):
        try:
            return _normalise(json.loads(attempt))
        except Exception:
            continue
    for attempt in (blob, no_commas):
        try:
            return _normalise(ast.literal_eval(attempt))   # literals only - nothing executes
        except Exception:
            continue
    return None


def _as_list(v, limit):
    if isinstance(v, str):
        v = [x.strip("-*• ").strip() for x in v.split("\n")]
    if not isinstance(v, list):
        return []
    return [str(x).strip() for x in v if str(x).strip()][:limit]


def _normalise(d):
    if not isinstance(d, dict):
        return None
    fmt = str(d.get("format") or "answer").strip().lower()
    if fmt not in ("slides", "answer", "document"):
        fmt = "answer"
    nr = d.get("needs_research")
    if isinstance(nr, str):
        nr = nr.strip().lower() in ("true", "yes", "evet", "1")
    return {
        "goal": str(d.get("goal") or "").strip(),
        "audience": str(d.get("audience") or "").strip(),
        "format": fmt,
        "needs_research": bool(nr),
        "research_queries": _as_list(d.get("research_queries") or d.get("queries"), MAX_RESEARCH_QUERIES),
        "outline": _as_list(d.get("outline") or d.get("sections"), MAX_OUTLINE),
        "tone": str(d.get("tone") or "").strip(),
    }


def plan_problems(plan, want_format=None):
    """Validation errors handed straight back to the model for the repair loop."""
    if not plan:
        return ["Output was not a JSON object with the required plan fields."]
    problems = []
    if not plan["goal"]:
        problems.append("'goal' is empty - state the goal in one sentence.")
    if want_format and plan["format"] != want_format:
        problems.append(f"'format' must be '{want_format}'.")
    if plan["format"] == "slides" and len(plan["outline"]) < 3:
        problems.append("'outline' needs at least 3 sections for a deck.")
    if plan["needs_research"] and not plan["research_queries"]:
        problems.append("needs_research is true but 'research_queries' is empty.")
    return problems


def default_plan(query, want_format="answer", memory_hit=False, audience=""):
    """Rule-built fallback plan. Used when the model's plan is unusable, so the system
    degrades to exactly the old fixed pipeline instead of failing."""
    return {
        "goal": query.strip()[:160],
        "audience": audience,
        "format": want_format,
        "needs_research": not memory_hit,          # nothing in the brain -> go look it up
        "research_queries": [query.strip()[:80]] if not memory_hit else [],
        "outline": [],
        "tone": "",
    }


def merge_plan(plan, rules):
    """Rules always win over the model on the things rules can decide."""
    out = dict(plan or {})
    out.update({k: v for k, v in rules.items() if v not in (None, "")})
    return out
