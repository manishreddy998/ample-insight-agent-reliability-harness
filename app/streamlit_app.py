import sys, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
import streamlit as st, pandas as pd
from agentrt.tools import Tools, INVENTORY
from agentrt.runtime import Runtime

st.set_page_config(page_title="Agent reliability harness", layout="wide")
st.title("Agent reliability harness")
st.caption("Synthetic retail tools with injected failures. Compare a naive agent loop with retries, schema checks and an approval gate.")
c1, c2, c3 = st.columns(3)
rate = c1.slider("Tool failure rate", 0.0, 0.5, 0.2, 0.05)
retries = c2.slider("Retries", 0, 3, 2)
validate = c3.checkbox("Validate arguments and outputs", True)
task = {"kind": "price_fx", "sku": st.selectbox("SKU", list(INVENTORY)[:20], index=3), "to": "USD", "qty": 10}
r = Runtime(Tools(failure_rate=rate, seed=4), retries=retries, validate=validate).run(task)
st.metric("Status", r["status"]); st.write("Answer", r["answer"])
st.subheader("Trace"); st.dataframe(pd.DataFrame(r["trace"]), use_container_width=True)
res = ROOT / "results.json"
if res.exists():
    data = json.loads(res.read_text()); rows = [{"failure_rate": k, "config": n, **v} for k, d in data.items() for n, v in d.items()]
    st.subheader("Eval over 300 tasks"); st.dataframe(pd.DataFrame(rows), use_container_width=True)
