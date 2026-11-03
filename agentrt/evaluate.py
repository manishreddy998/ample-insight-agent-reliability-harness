import json, random
from pathlib import Path
from .tools import Tools, INVENTORY
from .runtime import Runtime


def tasks(n=300, seed=5):
    rng = random.Random(seed); skus = list(INVENTORY); out = []
    for _ in range(n):
        k = rng.choice(["stock", "price_fx", "restock"])
        out.append({"kind": k, "sku": rng.choice(skus), "to": rng.choice(["USD", "EUR"]), "qty": rng.randint(5, 50)})
    return out


def expected(t):
    inv = INVENTORY[t["sku"]]
    if t["kind"] == "stock": return {"sku": t["sku"], "stock": inv["stock"]}
    if t["kind"] == "price_fx": return {"amount": round(inv["price"] * {"USD": .73, "EUR": .67}[t["to"]], 2), "to": t["to"]}
    return "skip" if inv["stock"] >= 10 else {"ok": True, "sku": t["sku"], "qty": t["qty"]}


def score(retries, validate, rate, seed=1):
    tools = Tools(failure_rate=rate, seed=seed); rt = Runtime(tools, retries=retries, validate=validate)
    ok = wrong = failed = 0
    for t in tasks():
        r = rt.run(t); e = expected(t)
        if r["status"] == "failed": failed += 1
        elif (e == "skip" and r["status"] == "skipped") or r["answer"] == e: ok += 1
        else: wrong += 1
    n = len(tasks())
    return {"correct": round(ok / n, 3), "silently_wrong": round(wrong / n, 3), "failed_loudly": round(failed / n, 3), "tool_calls": tools.calls}


def main():
    configs = {"naive (no retry, no validation)": (0, False), "validation only": (0, True), "retry 2 + validation": (2, True)}
    out = {}
    for rate in [0.0, 0.1, 0.2, 0.3]:
        out[str(rate)] = {name: score(r, v, rate) for name, (r, v) in configs.items()}
    Path("results.json").write_text(json.dumps(out, indent=2))
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 2, figsize=(9, 3.5))
    for name, c in zip(configs, ["#9aa5b1", "#f59e0b", "#2563eb"]):
        ax[0].plot([float(r) for r in out], [out[r][name]["correct"] for r in out], "o-", label=name, color=c)
        ax[1].plot([float(r) for r in out], [out[r][name]["silently_wrong"] for r in out], "o-", label=name, color=c)
    ax[0].set_title("Task success"); ax[1].set_title("Silently wrong answers")
    for a in ax: a.set_xlabel("injected tool failure rate"); a.grid(alpha=.3)
    ax[0].legend(fontsize=7); fig.tight_layout(); fig.savefig("docs/results.png", dpi=130)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
