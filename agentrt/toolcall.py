"""Real tool calling tasks from the Berkeley Function Calling Leaderboard (BFCL v3, Apache 2.0).

The local model reads a user request plus JSON tool schemas and must reply with one call.
The reliability layer checks the call against the schema (known tool, required args, types)
and, in the repair config, sends the exact error back to the model once."""
import json, random
from pathlib import Path
from .llm import get_backend

D = Path(__file__).resolve().parent.parent / "data"
TYPES = {"integer": int, "float": (int, float), "number": (int, float), "string": str, "boolean": bool, "array": list, "tuple": list, "dict": dict, "any": object}


def load(n_simple=25, n_multiple=15, n_irrelevant=15, seed=3):
    out = []
    irr = [json.loads(l) for l in (D / "BFCL_v3_irrelevance.json").open()]
    for q in random.Random(seed).sample(irr, n_irrelevant):
        out.append({"id": q["id"], "cat": "irrelevance", "request": q["question"][0][-1]["content"], "functions": q["function"], "gold": None})
    for cat, n in (("simple", n_simple), ("multiple", n_multiple)):
        qs = [json.loads(l) for l in (D / f"BFCL_v3_{cat}.json").open()]
        ans = {a["id"]: a["ground_truth"][0] for a in map(json.loads, (D / f"BFCL_v3_{cat}_answers.json").open())}
        for q in random.Random(seed).sample(qs, n):
            out.append({"id": q["id"], "cat": cat, "request": q["question"][0][-1]["content"], "functions": q["function"], "gold": ans[q["id"]]})
    return out


def validate(call, functions):
    """Return an error string, or None if the call fits a schema."""
    if not isinstance(call, dict) or "name" not in call or not isinstance(call.get("arguments"), dict):
        return 'reply must be {"name": ..., "arguments": {...}}'
    if call["name"] == "none":
        return None
    f = next((f for f in functions if f["name"] == call["name"]), None)
    if f is None:
        return f"unknown tool {call['name']!r}, choose one of {[x['name'] for x in functions]}"
    props, req = f["parameters"].get("properties", {}), f["parameters"].get("required", [])
    for r in req:
        if r not in call["arguments"]:
            return f"missing required argument {r!r} for {f['name']}"
    for k, v in call["arguments"].items():
        if k not in props:
            return f"unknown argument {k!r} for {f['name']}"
        t = TYPES.get(props[k].get("type"), object)
        if t is int and isinstance(v, bool) or not isinstance(v, t):
            return f"argument {k!r} must be {props[k].get('type')}, got {type(v).__name__}"
    return None


def _eq(v, allowed):
    for a in allowed:
        if a == v or (isinstance(a, (int, float)) and isinstance(v, (int, float)) and not isinstance(v, bool) and abs(a - v) < 1e-9):
            return True
        if isinstance(a, str) and isinstance(v, str) and a.strip().lower() == v.strip().lower():
            return True
    return False


def correct(call, gold):
    """None gold means no tool fits and the agent must abstain.
    BFCL style AST check: right tool, every given arg allowed, every mandatory gold arg present."""
    if gold is None:
        return isinstance(call, dict) and call.get("name") == "none"
    if not isinstance(call, dict) or call.get("name") not in gold:
        return False
    g, args = gold[call["name"]], call.get("arguments") or {}
    for k, allowed in g.items():
        if k in args:
            if not _eq(args[k], allowed):
                return False
        elif "" not in allowed:
            return False
    return all(k in g for k in args)


SYSTEM = ('You are a tool calling agent. Pick exactly one tool from the JSON schemas and reply only with JSON '
          '{"name": "<tool name>", "arguments": {<argument>: <value>}}. Use the exact types in the schema. '
          'If no tool can do the request, reply {"name": "none", "arguments": {}}.')


def prompt(t):
    return f"Tools:\n{json.dumps(t['functions'])}\n\nUser request: {t['request']}"


def run(task, mode, llm=None):
    llm = llm or get_backend()
    call = llm.complete_json(SYSTEM, prompt(task), num_predict=160)
    err = validate(call, task["functions"])
    attempts = 1
    if mode == "validate_repair" and err:
        call = llm.complete_json(SYSTEM, prompt(task) + f"\n\nYour previous reply {json.dumps(call)} was rejected: {err}. Reply again with a valid call.", num_predict=160)
        err = validate(call, task["functions"]); attempts = 2
    if mode == "naive":
        err = None
    status = "failed_loudly" if err else ("correct" if correct(call, task["gold"]) else "silently_wrong")
    return {"status": status, "call": call, "error": err, "attempts": attempts}
