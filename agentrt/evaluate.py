"""`python3 -m agentrt.evaluate` replays cached model calls; `LLM=ollama` runs live.
Scores 55 real BFCL v3 tasks (25 simple, 15 multiple choice of tool, 15 where no tool fits) in three configs."""
import json
from pathlib import Path
from .toolcall import load, run

MODES = {"naive": "naive (accept first reply)", "validate": "schema validation, fail loudly", "validate_repair": "validation + 1 repair retry"}


def main():
    tasks = load(); out, fails = {"n_tasks": len(tasks), "model": "qwen2.5-3b (Q4, CPU, Ollama)"}, {}
    for m in MODES:
        rows = [dict(run(t, m), id=t["id"], cat=t["cat"]) for t in tasks]
        agg = lambda rs: {k: round(sum(r["status"] == k for r in rs) / len(rs), 3) for k in ("correct", "silently_wrong", "failed_loudly")} | {"model_calls": sum(r["attempts"] for r in rs), "n": len(rs)}
        out[m] = {"all": agg(rows), "simple": agg([r for r in rows if r["cat"] == "simple"]), "multiple": agg([r for r in rows if r["cat"] == "multiple"]), "irrelevance": agg([r for r in rows if r["cat"] == "irrelevance"])}
        fails[m] = [r for r in rows if r["status"] != "correct"]
    Path("results.json").write_text(json.dumps(out, indent=2)); Path("docs/failures.json").write_text(json.dumps(fails, indent=1, default=str))
    print(json.dumps(out, indent=2)); return out


if __name__ == "__main__":
    main()
