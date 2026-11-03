from agentrt.toolcall import load, validate, correct
from agentrt.evaluate import main


def test_real_tasks_load():
    t = load(); assert len(t) == 55 and {x["cat"] for x in t} == {"simple", "multiple", "irrelevance"}


def test_validator():
    fn = [{"name": "f", "parameters": {"properties": {"x": {"type": "integer"}}, "required": ["x"]}}]
    assert validate({"name": "f", "arguments": {"x": 1}}, fn) is None
    assert "missing" in validate({"name": "f", "arguments": {}}, fn)
    assert "unknown tool" in validate({"name": "g", "arguments": {}}, fn)
    assert "must be" in validate({"name": "f", "arguments": {"x": "1"}}, fn)


def test_ast_check():
    g = {"f": {"x": [1], "unit": ["cm", ""]}}
    assert correct({"name": "f", "arguments": {"x": 1}}, g)
    assert not correct({"name": "f", "arguments": {"x": 2}}, g)
    assert correct({"name": "none", "arguments": {}}, None)


def test_eval_replays():
    assert main()["naive"]["all"]["n"] == 55
