#!/usr/bin/env python3
"""Normalize captured Hugging Face evidence into one deterministic observation.

This is intentionally the minimum issue #24 first-consumer identity gate. It does
not perform live provider access, artifact acquisition, drift persistence, or legal
interpretation.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


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
    if provenance.get("provider") != "huggingface":
        raise ValueError("provenance provider must be huggingface")

    request = provenance.get("request") or {}
    repository = request.get("repo")
    requested_revision = request.get("revision")
    if not repository or not requested_revision:
        raise ValueError("provenance must contain request.repo and request.revision")
    if fixture.get("id") != repository:
        raise ValueError("fixture repository identity does not match provenance request")

    source_revision = fixture.get("sha")
    if not isinstance(source_revision, str) or not SHA1_RE.fullmatch(source_revision):
        raise ValueError("fixture sha must be a full 40-hex repository commit")

    observed_at = provenance.get("captured_at")
    if not isinstance(observed_at, str) or not observed_at:
        raise ValueError("provenance must contain captured_at")

    files: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    for item in fixture.get("siblings", []):
        path = item.get("rfilename")
        if not isinstance(path, str) or not path:
            raise ValueError("each sibling must have rfilename")
        if path in seen_paths:
            raise ValueError(f"duplicate sibling path: {path}")
        seen_paths.add(path)

        normalized: dict[str, Any] = {"path": path}
        if "size" in item:
            size = item["size"]
            if not isinstance(size, int) or size < 0:
                raise ValueError(f"invalid size for {path}")
            normalized["size"] = size
        if "blobId" in item:
            blob_id = item["blobId"]
            if not isinstance(blob_id, str) or not SHA1_RE.fullmatch(blob_id):
                raise ValueError(f"invalid Git blob id for {path}")
            normalized["git_blob_id"] = blob_id

        lfs = item.get("lfs")
        if lfs:
            sha256 = lfs.get("sha256")
            lfs_size = lfs.get("size")
            if not isinstance(sha256, str) or not SHA256_RE.fullmatch(sha256):
                raise ValueError(f"invalid LFS sha256 for {path}")
            if not isinstance(lfs_size, int) or lfs_size < 0:
                raise ValueError(f"invalid LFS size for {path}")
            normalized["lfs"] = {"sha256": sha256.lower(), "size": lfs_size}

        files.append(normalized)

    files.sort(key=lambda item: item["path"])
    card_data = fixture.get("cardData") or {}

    return {
        "schema_version": 1,
        "provider": "huggingface",
        "locator": {
            "repository": repository,
            "requested_revision": requested_revision,
        },
        "observed_at": observed_at,
        "resolved": {
            "source_revision": source_revision,
            "identity_strength": "repository_commit",
        },
        "access": {
            "private": fixture.get("private"),
            "gated": fixture.get("gated"),
            "disabled": fixture.get("disabled"),
        },
        "declared_license": {
            "value": card_data.get("license"),
            "source": "huggingface-model-card-metadata",
            "interpretation": "declared-metadata-only",
        },
        "files": files,
        "evidence": {
            "fixture": fixture_ref,
            "provenance": provenance_ref,
        },
    }


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
