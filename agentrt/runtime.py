"""A small agent runtime: plan, validate args, call tools with retries,
validate outputs, enforce a step budget and an approval gate on side effects.

The planner is a deterministic rule planner standing in for an LLM planner.
The point is the reliability layer around it, which stays the same when an
LLM is plugged in.
"""
import time
from .tools import Tools, ToolError

EXPECTED_KEYS = {"get_stock": "stock", "get_price": "price", "convert_currency": "amount", "reorder": "ok"}


def plan(task):
    k = task["kind"]
    if k == "stock": return [("get_stock", {"sku": task["sku"]})]
    if k == "price_fx": return [("get_price", {"sku": task["sku"]}), ("convert_currency", {"amount": "$prev.price", "to": task["to"]})]
    if k == "restock": return [("get_stock", {"sku": task["sku"]}), ("reorder", {"sku": task["sku"], "qty": task["qty"]})]
    raise ValueError(k)


class Runtime:
    def __init__(self, tools: Tools, retries=2, validate=True, max_steps=6, approver=None):
        self.tools, self.retries, self.validate, self.max_steps = tools, retries, validate, max_steps
        self.approver = approver or (lambda call: True)

    def _call(self, name, args, trace):
        for attempt in range(self.retries + 1):
            t0 = time.perf_counter()
            try:
                out = getattr(self.tools, name)(**args)
                ok = (not self.validate) or EXPECTED_KEYS[name] in out
                trace.append({"tool": name, "attempt": attempt, "ok": ok, "ms": round((time.perf_counter() - t0) * 1000, 3)})
                if ok: return out
            except ToolError as e:
                trace.append({"tool": name, "attempt": attempt, "ok": False, "error": str(e)})
        raise ToolError(f"{name} failed after {self.retries + 1} attempts")

    def run(self, task):
        trace, prev = [], {}
        try:
            steps = plan(task)
            if len(steps) > self.max_steps: raise ToolError("step budget exceeded")
            for name, args in steps:
                args = {k: (prev.get(v[6:]) if isinstance(v, str) and v.startswith("$prev.") else v) for k, v in args.items()}
                for k, typ in Tools.schemas[name].items():
                    if self.validate and not isinstance(args.get(k), typ):
                        raise ToolError(f"bad argument {k} for {name}")
                if name == "reorder":
                    if prev.get("stock", 0) >= 10:
                        return {"status": "skipped", "answer": "stock sufficient", "trace": trace}
                    if not self.approver((name, args)):
                        return {"status": "needs_approval", "answer": None, "trace": trace}
                prev = self._call(name, args, trace)
            return {"status": "ok", "answer": prev, "trace": trace}
        except (ToolError, TypeError, KeyError) as e:
            return {"status": "failed", "answer": None, "error": str(e), "trace": trace}
