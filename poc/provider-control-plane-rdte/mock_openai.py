#!/usr/bin/env python3
import argparse
import json
import os
import signal
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def append_event(state_dir: Path, event: str, model_id: str, **extra):
    state_dir.mkdir(parents=True, exist_ok=True)
    record = {
        "ts": time.time(),
        "event": event,
        "model": model_id,
        **extra,
    }
    with (state_dir / "events.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")
        fh.flush()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--model-id", required=True)
    ap.add_argument("--state-dir", required=True)
    args = ap.parse_args()

    state_dir = Path(args.state_dir)
    append_event(state_dir, "start", args.model_id, pid=os.getpid())

    class Handler(BaseHTTPRequestHandler):
        def _json(self, code, obj):
            payload = json.dumps(obj).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            append_event(state_dir, "request", args.model_id, method="GET", path=self.path)
            if self.path in ("/health", "/ready", "/readyz"):
                self._json(200, {"status": "ok", "model": args.model_id})
                return
            if self.path == "/v1/models":
                self._json(200, {
                    "object": "list",
                    "data": [{"id": args.model_id, "object": "model"}],
                })
                return
            self._json(404, {"error": "not found"})

        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length else b"{}"
            try:
                body = json.loads(raw.decode("utf-8"))
            except Exception:
                body = {}
            append_event(
                state_dir,
                "request",
                args.model_id,
                method="POST",
                path=self.path,
                requested_model=body.get("model"),
            )
            if self.path == "/v1/chat/completions":
                self._json(200, {
                    "id": "mock-completion",
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": args.model_id,
                    "choices": [{
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": f"served-by:{args.model_id}",
                        },
                        "finish_reason": "stop",
                    }],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                })
                return
            self._json(404, {"error": "not found"})

        def log_message(self, fmt, *values):
            return

    def stop(signum, frame):
        append_event(state_dir, "stop", args.model_id, pid=os.getpid(), signal=signum)
        sys.exit(0)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    try:
        server.serve_forever(poll_interval=0.1)
    finally:
        append_event(state_dir, "exit", args.model_id, pid=os.getpid())


if __name__ == "__main__":
    main()
