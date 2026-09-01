#!/usr/bin/env python3
"""Offline safety/shape checks for issue #12 metadata fixtures."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from capture_provider_metadata import require_public_safe

FORBIDDEN_SUFFIXES = {
    ".bin",
    ".ckpt",
    ".gguf",
    ".onnx",
    ".pt",
    ".pth",
    ".safetensors",
    ".tar",
    ".tgz",
    ".zip",
}


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    fixture_root = repo_root / "fixtures" / "raw"
    failures: list[str] = []
    json_files = sorted(fixture_root.rglob("*.json"))
    if not json_files:
        failures.append("no JSON fixtures found")

    for path in sorted(fixture_root.rglob("*")):
        if path.is_file() and path.suffix.lower() in FORBIDDEN_SUFFIXES:
            failures.append(f"model/archive bytes forbidden under fixtures/raw: {path.relative_to(repo_root)}")

    for path in json_files:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            require_public_safe(value)
        except Exception as exc:
            failures.append(f"{path.relative_to(repo_root)}: {exc}")

    if failures:
        print("fixture validation failed:", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1

    print(f"validated {len(json_files)} JSON fixture/provenance files; no forbidden model/archive bytes found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
