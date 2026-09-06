#!/usr/bin/env python3
"""Fail closed on obvious local/private metadata before public publication.

This is defense in depth. It scans only files explicitly supplied by the caller
and does not discover hosts, files, networks, repositories, or environment state.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("unix-home-path", re.compile(r"(?<!https:)(?<!http:)(?:/home/|/Users/)[A-Za-z0-9._-]+(?:/|\b)")),
    ("local-mount-path", re.compile(r"(?:^|[\s\"'=])/(?:mnt|media|srv|volume\d*)/[A-Za-z0-9._/-]+", re.MULTILINE)),
    ("windows-user-path", re.compile(r"[A-Za-z]:\\(?:Users|Documents and Settings)\\[^\\\s]+", re.IGNORECASE)),
    ("rfc1918-ip", re.compile(r"\b(?:10(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2})\b")),
    ("link-local-ip", re.compile(r"\b169\.254(?:\.\d{1,3}){2}\b")),
    ("mac-address", re.compile(r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b")),
    ("gpu-device-uuid", re.compile(r"\bGPU-[0-9a-fA-F-]{16,}\b")),
    ("local-dns", re.compile(r"\b[A-Za-z0-9._-]+\.(?:local|lan|home|internal)\b", re.IGNORECASE)),
    ("tailscale-dns", re.compile(r"\b[A-Za-z0-9.-]+\.ts\.net\b", re.IGNORECASE)),
    ("environment-dump", re.compile(r"(?m)^(?:HOME|USER|USERNAME|HOSTNAME|SSH_CONNECTION|SSH_CLIENT|PWD|TAILSCALE_[A-Z0-9_]+)=")),
    ("credential-like", re.compile(r"(?i)\b(?:token|password|passwd|secret|api[_-]?key)\s*[:=]\s*[\"']?[A-Za-z0-9_./+=-]{12,}")),
]


def lint_text(text: str) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for kind, pattern in PATTERNS:
        for match in pattern.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            sample = match.group(0).strip()
            if len(sample) > 120:
                sample = sample[:117] + "..."
            findings.append({"kind": kind, "line": line, "sample": sample})
    return findings


def lint_file(path: Path) -> list[dict[str, object]]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        json.loads(text)
    return lint_text(text)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", help="public metadata files to lint")
    args = parser.parse_args()

    failed = False
    for raw in args.paths:
        path = Path(raw)
        findings = lint_file(path)
        if findings:
            failed = True
            print(json.dumps({"path": str(path), "findings": findings}, sort_keys=True))
    if failed:
        return 2
    print(json.dumps({"status": "passed", "files": args.paths}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
