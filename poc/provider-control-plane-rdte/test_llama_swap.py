#!/usr/bin/env python3
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = os.environ.get("LLAMA_SWAP_URL", "http://127.0.0.1:18080")
STATE = Path(os.environ["RDTE_STATE_DIR"])
RECEIPT = Path(os.environ.get("RDTE_LLAMA_RECEIPT", "llama-swap-receipt.json"))


def http_json(method, path, body=None):
    data = None
    headers = {"Content-Type": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_ready(timeout=20):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        try:
            return http_json("GET", "/v1/models")
        except Exception as exc:
            last = exc
            time.sleep(0.25)
    raise RuntimeError(f"llama-swap did not become ready: {last}")


def chat(model):
    response = http_json("POST", "/v1/chat/completions", {
        "model": model,
        "messages": [{"role": "user", "content": "ping"}],
        "temperature": 0,
        "max_tokens": 4,
    })
    return response["choices"][0]["message"]["content"]


def events():
    path = STATE / "events.jsonl"
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def count(event, model):
    return sum(1 for x in events() if x.get("event") == event and x.get("model") == model)


def wait_event(event, model, minimum=1, timeout=10):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if count(event, model) >= minimum:
            return
        time.sleep(0.2)
    raise AssertionError(f"missing event={event!r} model={model!r}; events={events()}")


checks = {}
models = wait_ready()
ids = {x["id"] for x in models.get("data", [])}
assert "auto-code" in ids, ids
assert "auto-general" in ids, ids
checks["virtual_model_ids"] = True

content = chat("auto-code")
assert content == "served-by:code-a", content
wait_event("start", "code-a")
checks["selector_cold_start"] = True

content = chat("code-b")
assert content == "served-by:code-b", content
wait_event("start", "code-b")
wait_event("stop", "code-a")
checks["matrix_eviction"] = True

code_a_starts = count("start", "code-a")
content = chat("auto-code")
assert content == "served-by:code-b", content
time.sleep(0.5)
assert count("start", "code-a") == code_a_starts, events()
checks["warm_selector_preference"] = True

content = chat("auto-general")
assert content == "served-by:general-a", content
wait_event("start", "general-a")
wait_event("stop", "code-b")
checks["stable_general_selector"] = True

wait_event("stop", "general-a", timeout=8)
checks["ttl_idle_unload"] = True
checks["openai_proxy"] = True

receipt = {
    "candidate": "llama-swap",
    "release": "v262",
    "commit": "079c35ae82fb2816d319f7bd16936675597b262d",
    "checks": checks,
    "events": events(),
}
RECEIPT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(receipt, indent=2, sort_keys=True))
