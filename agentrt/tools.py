"""Tool registry with JSON style schemas and seeded failure injection.

Tools are deterministic local functions over a SYNTHETIC retail dataset, so
the harness can measure the runtime, not a model's mood. Failures simulate
timeouts, malformed payloads and rate limits at a set rate.
"""
import random

INVENTORY = {f"SKU{i:03d}": {"stock": (i * 7) % 23, "price": round(5 + (i * 3.7) % 40, 2), "store": ["TOR", "MTL", "VAN"][i % 3]} for i in range(60)}


class ToolError(Exception):
    pass


class Tools:
    schemas = {
        "get_stock": {"sku": str},
        "get_price": {"sku": str},
        "convert_currency": {"amount": float, "to": str},
        "reorder": {"sku": str, "qty": int},
    }
    side_effects = {"reorder"}

    def __init__(self, failure_rate=0.0, seed=0):
        self.rng = random.Random(seed); self.failure_rate = failure_rate; self.calls = 0; self.reorders = []

    def _maybe_fail(self):
        self.calls += 1
        if self.rng.random() < self.failure_rate:
            kind = self.rng.choice(["timeout", "malformed", "rate_limit"])
            if kind == "malformed":
                return {"garbage": True}
            raise ToolError(kind)
        return None

    def get_stock(self, sku):
        bad = self._maybe_fail()
        return bad if bad else {"sku": sku, "stock": INVENTORY[sku]["stock"]}

    def get_price(self, sku):
        bad = self._maybe_fail()
        return bad if bad else {"sku": sku, "price": INVENTORY[sku]["price"]}

    def convert_currency(self, amount, to):
        bad = self._maybe_fail()
        return bad if bad else {"amount": round(amount * {"USD": 0.73, "EUR": 0.67, "CAD": 1.0}[to], 2), "to": to}

    def reorder(self, sku, qty):
        bad = self._maybe_fail()
        if bad: return bad
        self.reorders.append((sku, qty)); return {"ok": True, "sku": sku, "qty": qty}
