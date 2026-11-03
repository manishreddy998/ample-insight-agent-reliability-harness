import sys, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
import streamlit as st, pandas as pd
from agentrt.tools import Tools, INVENTORY
from agentrt.runtime import Runtime

st.set_page_config(page_title="Agent reliability harness", layout="wide")
st.title("Agent reliability harness")
from agentrt.toolcall import load, run
st.header("Real tool calling tasks")
st.caption("55 tasks from the Berkeley Function Calling Leaderboard v3 (Hugging Face gorilla-llm/Berkeley-Function-Calling-Leaderboard, Apache 2.0). Model: local Qwen2.5 3B, replayed from cache.")
tasks = load(); tid = st.selectbox("Task", [t["id"] for t in tasks], index=40)
t = next(x for x in tasks if x["id"] == tid); st.write("Request:", t["request"])
m = st.radio("Config", ["naive", "validate", "validate_repair"], horizontal=True, index=2)
st.json(run(t, m)); st.write("Gold:", t["gold"] or "no tool fits, must abstain")
real = json.loads((ROOT / "results.json").read_text())
st.dataframe(pd.DataFrame([{"config": k, "slice": c, **real[k][c]} for k in ["naive", "validate", "validate_repair"] for c in ["all", "simple", "multiple", "irrelevance"]]), use_container_width=True)
st.header("Failure injection simulation (synthetic tools)")
st.caption("SYNTHETIC retail tools with injected failures. Compare a naive agent loop with retries, schema checks and an approval gate.")
c1, c2, c3 = st.columns(3)
rate = c1.slider("Tool failure rate", 0.0, 0.5, 0.2, 0.05)
retries = c2.slider("Retries", 0, 3, 2)
validate = c3.checkbox("Validate arguments and outputs", True)
task = {"kind": "price_fx", "sku": st.selectbox("SKU", list(INVENTORY)[:20], index=3), "to": "USD", "qty": 10}
r = Runtime(Tools(failure_rate=rate, seed=4), retries=retries, validate=validate).run(task)
st.metric("Status", r["status"]); st.write("Answer", r["answer"])
st.subheader("Trace"); st.dataframe(pd.DataFrame(r["trace"]), use_container_width=True)
res = ROOT / "results_simulation.json"
if res.exists():
    data = json.loads(res.read_text()); rows = [{"failure_rate": k, "config": n, **v} for k, d in data.items() for n, v in d.items()]
    st.subheader("Eval over 300 tasks"); st.dataframe(pd.DataFrame(rows), use_container_width=True)
