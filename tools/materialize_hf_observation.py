#!/usr/bin/env python3
"""Materialize one normalized exact Hugging Face observation into the native cache."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from provider_adapters.hf_native import (
    HuggingFaceCacheMiss,
    HuggingFaceSnapshotVerificationError,
    canonical_json,
    ensure_hf_native_snapshot,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--observation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument(
        "--allow-network",
        action="store_true",
        help="Opt in to exact-revision Hub download after a native-cache miss.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    observation = json.loads(args.observation.read_text(encoding="utf-8"))
    try:
        receipt = ensure_hf_native_snapshot(
            observation,
            allow_network=args.allow_network,
            cache_dir=args.cache_dir,
        )
    except (ValueError, HuggingFaceCacheMiss, HuggingFaceSnapshotVerificationError) as exc:
        print(f"materialization failed: {exc}", file=sys.stderr)
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    tmp = args.output.with_suffix(args.output.suffix + ".tmp")
    tmp.write_text(canonical_json(receipt), encoding="utf-8")
    tmp.replace(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
