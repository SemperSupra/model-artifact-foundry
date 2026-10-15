#!/usr/bin/env python3
"""Adopt already-authorized local gated artifact bytes into Foundry identity.

This tool is intentionally offline. It never authenticates to an upstream
provider, accepts terms, downloads model files, or persists credentials/local
absolute paths. It produces a deterministic content-manifest identity.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_declaration(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    policy = data.get("acquisition_policy") or {}
    if policy.get("mode") != "consumer-authenticated-local":
        raise RuntimeError("declaration is not a consumer-authenticated-local source")
    for field in ("public_harvest", "public_redistribution", "public_package_publication"):
        if policy.get(field) is not False:
            raise RuntimeError(f"gated declaration must fail closed for {field}")
    local_identity = data.get("local_identity") or {}
    if local_identity.get("require_exact_upstream_revision") is not True:
        raise RuntimeError("gated declaration must require an exact upstream revision")
    if local_identity.get("digest_kind") != "content-manifest" or local_identity.get("hash_algorithm") != "sha256":
        raise RuntimeError("unsupported local identity contract")
    return data


def enumerate_files(root: Path) -> list[dict[str, Any]]:
    root = root.resolve()
    if not root.is_dir():
        raise RuntimeError(f"artifact directory does not exist or is not a directory: {root}")

    records: list[dict[str, Any]] = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        current = Path(dirpath)
        # Reject symlinked directories rather than silently skipping or following.
        for name in list(dirnames):
            path = current / name
            if path.is_symlink():
                raise RuntimeError(f"symlinked directories are not allowed: {path.relative_to(root).as_posix()}")
        for name in filenames:
            path = current / name
            rel = path.relative_to(root).as_posix()
            if path.is_symlink():
                raise RuntimeError(f"symlinked files are not allowed: {rel}")
            if not path.is_file():
                raise RuntimeError(f"non-regular artifact member: {rel}")
            records.append({
                "path": rel,
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            })

    records.sort(key=lambda item: item["path"])
    if not records:
        raise RuntimeError("artifact directory contains no regular files")
    return records


def canonical_identity_material(
    declaration: dict[str, Any], exact_revision: str, files: list[dict[str, Any]]
) -> dict[str, Any]:
    if len(exact_revision.strip()) < 7:
        raise RuntimeError("exact upstream revision must contain at least 7 characters")
    return {
        "schema_version": 1,
        "logical_id": declaration["logical_id"],
        "upstream": {
            "provider": declaration["source"]["provider"],
            "repository": declaration["source"]["repository"],
            "exact_revision": exact_revision.strip(),
        },
        "files": files,
    }


def content_manifest_digest(material: dict[str, Any]) -> str:
    canonical = json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(canonical).hexdigest()


def adopt_file_records(
    declaration: dict[str, Any], files: list[dict[str, Any]], exact_revision: str
) -> dict[str, Any]:
    """Reuse the canonical identity/receipt for independently verified native-cache bytes."""
    material = canonical_identity_material(declaration, exact_revision, files)
    digest = content_manifest_digest(material)
    return {
        "schema_version": 1,
        "logical_id": declaration["logical_id"],
        "artifact_identity": {
            "kind": "content-manifest",
            "digest": digest,
        },
        "upstream": material["upstream"],
        "access": {
            "mode": declaration["access"]["mode"],
        },
        "files": files,
        "redistribution": {
            "public_publish_allowed": False,
        },
    }



def verify_local_adoption_receipt(record: dict[str, Any], expected_digest: str) -> dict[str, Any]:
    """Verify received Foundry identity/material, NOT the underlying local file bytes.

    A consumer must separately have Foundry rehash native cache bytes before
    treating this receipt as current. The expected digest is retained authority
    from a distinct channel; self-consistent but unapproved identity is not enough.
    """
    import re
    from pathlib import PurePosixPath

    digest_re = re.compile(r"sha256:[0-9a-f]{64}\Z")
    if not isinstance(expected_digest, str) or not digest_re.fullmatch(expected_digest):
        raise ValueError("Missing immutable authorized expected content-manifest digest")
    if not isinstance(record, dict) or set(record) != {
        "schema_version", "logical_id", "upstream", "access",
        "files", "artifact_identity", "redistribution"
    } or record.get("schema_version") != 1:
        raise ValueError("Unexpected or incomplete local adoption receipt")
    identity = record["artifact_identity"]
    if identity != {"kind": "content-manifest", "digest": expected_digest}:
        raise ValueError("Local content identity not exact approved subject")
    if record["redistribution"] != {"public_publish_allowed": False}:
        raise ValueError("Missing explicit nonpublication hold")
    if record["access"] not in (
        {"mode": "restricted"}, {"mode": "user-accepted-gated"}, {"mode": "authenticated-gated"}
    ):
        raise ValueError("Unknown local-only access mode")
    logical = record["logical_id"]
    if not isinstance(logical, str) or not re.fullmatch(r"[a-z0-9][a-z0-9._/-]{2,}", logical):
        raise ValueError("Unsafe or absent logical artifact ID")
    upstream = record["upstream"]
    if not isinstance(upstream, dict) or set(upstream) != {"provider", "repository", "exact_revision"}:
        raise ValueError("Incomplete upstream identity")
    if upstream["provider"] not in ("huggingface", "github-release", "https", "other"):
        raise ValueError("Unrecognized source provider")
    if not isinstance(upstream["repository"], str) or not upstream["repository"].strip():
        raise ValueError("Missing origin repository")
    revision = upstream["exact_revision"]
    if not isinstance(revision, str) or revision != revision.strip() or len(revision) < 7:
        raise ValueError("Unpinned upstream revision")
    files = record["files"]
    if not isinstance(files, list) or not 1 <= len(files) <= 10000:
        raise ValueError("Empty or oversized receipt file list")
    total = 0
    previous = ""
    for row in files:
        if not isinstance(row, dict) or set(row) != {"path", "size_bytes", "sha256"}:
            raise ValueError("Malformed file identity")
        path = row["path"]
        if not isinstance(path, str) or not path or chr(92) in path or chr(0) in path:
            raise ValueError("Unsafe file path")
        pure = PurePosixPath(path)
        if pure.is_absolute() or not pure.parts or any(p in ("..", ".") for p in path.split("/")):
            raise ValueError("Absolute or traversing model path")
        if path != pure.as_posix() or path <= previous:
            raise ValueError("Noncanonical or duplicate model file paths")
        previous = path
        size = row["size_bytes"]
        if type(size) is not int or size < 0:
            raise ValueError("Invalid model file length")
        total += size
        if total > 20 * 1024 * 1024 * 1024:
            raise ValueError("Model inventory size budget exceeded")
        sha = row["sha256"]
        if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{64}", sha):
            raise ValueError("Missing model file checksum")
    calculated = content_manifest_digest({
        "schema_version": 1,
        "logical_id": logical,
        "upstream": upstream,
        "files": files,
    })
    if calculated != expected_digest:
        raise ValueError("File identities do not match frozen Foundry content-manifest digest")
    return {
        "schema": "foundry-local-adoption-receipt-verification/v1",
        "result": "RECEIPT_INTEGRITY_PASS_NOT_CACHE_BYTE_REHASH",
        "artifact_identity": {"kind": "content-manifest", "digest": calculated},
        "files": len(files), "public_publish_allowed": False,
    }


def adopt(declaration: dict[str, Any], root: Path, exact_revision: str) -> dict[str, Any]:
    return adopt_file_records(declaration, enumerate_files(root), exact_revision)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--declaration", type=Path, required=True)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    declaration = load_declaration(args.declaration)
    record = adopt(declaration, args.directory, args.source_revision)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "logical_id": record["logical_id"],
        "artifact_identity": record["artifact_identity"],
        "files": len(record["files"]),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
