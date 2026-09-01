#!/usr/bin/env python3
"""Normalize captured Hugging Face evidence into one deterministic observation.

This remains the issue #24 backward-compatible CLI/API surface. Provider-specific
evidence interpretation lives behind the in-tree Hugging Face adapter so the core
observation contract is not coupled to provider SDK/types. This does not add live
provider access, artifact acquisition, plugin discovery, or separately distributed
provider packages.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from provider_adapters.huggingface import HUGGINGFACE_ADAPTER


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def stable_evidence_ref(path: Path) -> str:
    """Return a machine-independent evidence reference when possible."""
    parts = path.as_posix().split("/")
    if "fixtures" in parts:
        return "/".join(parts[parts.index("fixtures") :])
    return path.name if path.is_absolute() else path.as_posix()


def normalize_hf_observation(
    fixture: dict[str, Any],
    provenance: dict[str, Any],
    *,
    fixture_ref: str,
    provenance_ref: str,
) -> dict[str, Any]:
    """Backward-compatible wrapper around the explicit in-tree HF adapter."""
    return HUGGINGFACE_ADAPTER.normalize_observation(
        fixture,
        provenance,
        fixture_ref=fixture_ref,
        provenance_ref=provenance_ref,
    )


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--fixture", required=True, type=Path)
    result.add_argument("--provenance", required=True, type=Path)
    result.add_argument("--output", type=Path)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        observation = normalize_hf_observation(
            load_json(args.fixture),
            load_json(args.provenance),
            fixture_ref=stable_evidence_ref(args.fixture),
            provenance_ref=stable_evidence_ref(args.provenance),
        )
        payload = canonical_json(observation)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(payload, encoding="utf-8", newline="\n")
        else:
            sys.stdout.write(payload)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
