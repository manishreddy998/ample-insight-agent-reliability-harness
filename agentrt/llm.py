"""Local LLM backend with a replay cache.

OllamaBackend calls a local Qwen2.5 3B Instruct (Q4, Apache 2.0) over HTTP on CPU.
Every reply is cached by model plus prompt hash in data/llm_cache.json, so the eval,
tests and UI replay the exact measured outputs without a model. Set LLM=ollama to run live.
"""
import hashlib, json, os, urllib.request
from pathlib import Path

CACHE = Path(__file__).resolve().parent.parent / "data" / "llm_cache.json"


def _key(model, system, prompt):
    return hashlib.sha256(f"{model}\n{system}\n{prompt}".encode()).hexdigest()[:24]


class OllamaBackend:
    live = True

    def __init__(self, model=None, host=None):
        self.model = model or os.environ.get("LLM_MODEL", "qwen2.5-3b")
        self.host = host or os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
        self.d = json.loads(CACHE.read_text()) if CACHE.exists() else {}

    def complete_json(self, system, prompt, num_predict=96):
        k = _key(self.model, system, prompt)
        if k not in self.d:
            if not self.live:
                raise KeyError("prompt not in cache, run with LLM=ollama")
            body = {"model": self.model, "stream": False, "format": "json",
                    "options": {"temperature": 0, "num_ctx": 4096, "num_predict": num_predict},
                    "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]}
            req = urllib.request.Request(self.host + "/api/chat", json.dumps(body).encode(), {"Content-Type": "application/json"})
            self.d[k] = json.loads(urllib.request.urlopen(req, timeout=600).read())["message"]["content"]
            CACHE.parent.mkdir(exist_ok=True)
            CACHE.write_text(json.dumps(self.d, indent=0, sort_keys=True))
        try:
            return json.loads(self.d[k])
        except Exception:
            return {}


class ReplayBackend(OllamaBackend):
    live = False


def get_backend():
    return OllamaBackend() if os.environ.get("LLM") == "ollama" else ReplayBackend()
