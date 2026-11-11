#!/usr/bin/env python3
"""Offline, no-copy content identity for an exact Hugging Face native snapshot.

Not a model downloader, an approval decision, a packager, or a replacement for
provider-native snapshot acquisition. Direct files and symlink-backed HF blobs
are hashed under a strictly bounded native hub cache. No model bytes are copied
or uploaded. Reuses the Foundry's canonical local-adoption receipt.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

from adopt_local_artifact import adopt_file_records, load_declaration, sha256_file

_REV = re.compile(r"^[0-9a-f]{40}$")
_REPO_PART = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_MAX_FILES = 10000
_MAX_BYTES = 20 * 1024 * 1024 * 1024


def _under(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def enumerate_native_hf_snapshot(hub_cache: Path, repository: str, revision: str) -> list[dict]:
    """Return stable logical snapshot paths, even when bytes reside in HF blobs."""
    if not _REV.fullmatch(revision):
        raise ValueError("Hugging Face source revision must be the full 40-hex commit")
    parts = repository.split("/")
    if len(parts) != 2 or not all(_REPO_PART.fullmatch(p) and p not in (".", "..") for p in parts):
        raise ValueError("Expected an exact owner/repository identity")
    if hub_cache.is_symlink() or not hub_cache.is_dir():
        raise ValueError("Native hub-cache root must be a real directory")
    hub = hub_cache.resolve(strict=True)
    source = hub / ("models--" + "--".join(parts))
    snapshot = source / "snapshots" / revision
    if source.is_symlink() or snapshot.is_symlink() or not snapshot.is_dir():
        raise ValueError("Exact snapshot is absent or unsafe")
    allowed_blob_roots = (source / "blobs", hub / "blobs")
    # All expected native cache directories must be real, not substituted links.
    for path in (source, source / "snapshots"):
        if path.is_symlink():
            raise ValueError("Native snapshot path cannot be a symlink")
    rows: list[dict] = []
    total = 0
    for folder, dirs, files in os.walk(snapshot, followlinks=False):
        dirs.sort()
        files.sort()
        for name in dirs:
            if (Path(folder) / name).is_symlink():
                raise ValueError("Symlinked directories are not a native HF snapshot contract")
        for name in files:
            item = Path(folder) / name
            rel = item.relative_to(snapshot).as_posix()
            if item.is_symlink():
                if os.path.isabs(os.readlink(item)):
                    raise ValueError("Absolute snapshot file symlink not allowed: " + rel)
                real = item.resolve(strict=True)
                if not any(_under(real, p) for p in allowed_blob_roots):
                    raise ValueError("Snapshot symlink escapes approved HF blobs: " + rel)
            else:
                real = item.resolve(strict=True)
                if not _under(real, snapshot):
                    raise ValueError("Native snapshot file escapes snapshot root")
            if not real.is_file():
                raise ValueError("Non-regular snapshot content: " + rel)
            size = real.stat().st_size
            total += size
            if len(rows) >= _MAX_FILES or total > _MAX_BYTES:
                raise ValueError("Exceeded bounded native snapshot inventory budget")
            rows.append({"path": rel, "size_bytes": size, "sha256": sha256_file(real)})
    if not rows:
        raise ValueError("No model snapshot files")
    return rows


def adopt_native_snapshot(declaration: dict, hub_cache: Path, revision: str) -> dict:
    if declaration.get("source", {}).get("provider") != "huggingface":
        raise ValueError("Only Hugging Face declarations are accepted")
    repo = declaration["source"]["repository"]
    rows = enumerate_native_hf_snapshot(hub_cache, repo, revision)
    return adopt_file_records(declaration, rows, revision)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--declaration", type=Path, required=True)
    p.add_argument("--hub-cache", type=Path, required=True)
    p.add_argument("--source-revision", required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    declaration = load_declaration(a.declaration)
    record = adopt_native_snapshot(declaration, a.hub_cache, a.source_revision)
    if a.output.exists():
        raise FileExistsError("Do not replace an existing evidence receipt")
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"logical_id": record["logical_id"],
                      "artifact_identity": record["artifact_identity"],
                      "files": len(record["files"]),
                      "publication": "DISABLED"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
