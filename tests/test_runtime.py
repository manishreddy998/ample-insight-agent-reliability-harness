from agentrt.tools import Tools
from agentrt.runtime import Runtime
from agentrt.evaluate import score


def test_no_failures_all_correct():
    assert score(2, True, 0.0)["correct"] == 1.0


def test_validation_removes_silent_errors():
    assert score(2, True, 0.3)["silently_wrong"] == 0.0
    assert score(0, False, 0.3)["silently_wrong"] > 0


def test_reorder_needs_approval():
    rt = Runtime(Tools(), approver=lambda call: False)
    r = rt.run({"kind": "restock", "sku": "SKU000", "qty": 5})  # SKU000 stock 0
    assert r["status"] == "needs_approval" and rt.tools.reorders == []
