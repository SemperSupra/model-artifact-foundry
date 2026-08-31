#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import uuid

BUNDLE_FILES = {"model.tar.gz", "bundle-manifest.json", "NOTICE.txt"}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_name(logical_id: str) -> str:
    return logical_id.replace("/", "__").replace(":", "_")


def resolve_bundle_dir(root: Path) -> Path:
    matches = []
    for candidate in (root, root / "dist"):
        if not candidate.is_dir():
            continue
        actual = {p.name for p in candidate.iterdir() if p.is_file()}
        if actual == BUNDLE_FILES:
            matches.append(candidate)
    if len(matches) != 1:
        layouts = []
        for candidate in (root, root / "dist"):
            if candidate.is_dir():
                layouts.append(f"{candidate}: {sorted(p.name for p in candidate.iterdir())}")
        raise RuntimeError(f"unable to resolve exactly one approved OCI layer layout: {layouts}")
    return matches[0]


def safe_extract(archive: Path, dest: Path, expected_names: set[str]) -> None:
    dest_abs = dest.resolve()
    with tarfile.open(archive, "r:gz") as tf:
        names = set(tf.getnames())
        if names != expected_names:
            raise RuntimeError(f"archive file set mismatch: {sorted(names)}")
        for member in tf.getmembers():
            target = (dest / member.name).resolve()
            if dest_abs != target and dest_abs not in target.parents:
                raise RuntimeError(f"unsafe archive path: {member.name}")
            if not member.isfile():
                raise RuntimeError(f"non-regular archive member: {member.name}")
        tf.extractall(dest)


def verify_model_dir(model_dir: Path, manifest: dict) -> None:
    expected = {entry["path"]: entry for entry in manifest["files"]}
    actual = {p.name for p in model_dir.iterdir() if p.is_file()}
    if actual != set(expected):
        raise RuntimeError(f"model directory file set mismatch: {sorted(actual)}")
    for name, entry in expected.items():
        p = model_dir / name
        if p.stat().st_size != entry["size_bytes"]:
            raise RuntimeError(f"size mismatch for {name}")
        if sha256_file(p) != entry["sha256"]:
            raise RuntimeError(f"hash mismatch for {name}")


def atomic_write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def update_selection(cache_root: Path, logical_id: str, digest: str, model_dir: Path) -> None:
    atomic_write_json(
        cache_root / "selected" / f"{safe_name(logical_id)}.json",
        {"schema_version": 1, "logical_id": logical_id, "digest": digest, "model_dir": str(model_dir)},
    )


def hydrate(catalog_path: Path, logical_id: str, cache_root: Path, oras: str) -> Path:
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    entry = catalog["artifacts"].get(logical_id)
    if not entry:
        raise RuntimeError(f"logical artifact is not approved: {logical_id}")

    digest = entry["approved_digest"]
    repository = entry["oci_repository"]
    digest_dir = digest.replace(":", "-")
    final_dir = cache_root / "blobs" / digest_dir
    model_dir = final_dir / "model"
    marker = final_dir / ".verified.json"

    if final_dir.exists() and marker.exists():
        marker_data = json.loads(marker.read_text(encoding="utf-8"))
        if marker_data.get("digest") == digest:
            manifest = json.loads((final_dir / "bundle-manifest.json").read_text(encoding="utf-8"))
            verify_model_dir(model_dir, manifest)
            update_selection(cache_root, logical_id, digest, model_dir)
            print(model_dir)
            return model_dir

    staging_root = cache_root / ".staging"
    staging_root.mkdir(parents=True, exist_ok=True)
    staging = staging_root / f"{safe_name(logical_id)}-{uuid.uuid4().hex}"
    pulled = staging / "pulled"
    extracted = staging / "artifact"
    model_stage = extracted / "model"
    pulled.mkdir(parents=True)
    model_stage.mkdir(parents=True)

    try:
        target = f"{repository}@{digest}"
        subprocess.run([oras, "pull", target, "--output", str(pulled)], check=True)
        bundle_dir = resolve_bundle_dir(pulled)

        manifest = json.loads((bundle_dir / "bundle-manifest.json").read_text(encoding="utf-8"))
        if manifest["logical_id"] != logical_id:
            raise RuntimeError("bundle logical ID does not match catalog selection")
        if manifest["upstream"]["exact_revision"] != entry["upstream_exact_revision"]:
            raise RuntimeError("bundle upstream revision does not match approved catalog")

        archive = bundle_dir / "model.tar.gz"
        if sha256_file(archive) != manifest["archive"]["sha256"]:
            raise RuntimeError("bundle archive hash mismatch")
        safe_extract(archive, model_stage, {x["path"] for x in manifest["files"]})
        verify_model_dir(model_stage, manifest)

        shutil.copy2(bundle_dir / "bundle-manifest.json", extracted / "bundle-manifest.json")
        shutil.copy2(bundle_dir / "NOTICE.txt", extracted / "NOTICE.txt")
        atomic_write_json(
            extracted / ".verified.json",
            {
                "schema_version": 1,
                "logical_id": logical_id,
                "digest": digest,
                "oci_repository": repository,
                "upstream_exact_revision": manifest["upstream"]["exact_revision"],
            },
        )

        final_dir.parent.mkdir(parents=True, exist_ok=True)
        if final_dir.exists():
            shutil.rmtree(final_dir)
        os.replace(extracted, final_dir)
        update_selection(cache_root, logical_id, digest, final_dir / "model")
        print(final_dir / "model")
        return final_dir / "model"
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Hydrate one approved Foundry artifact by immutable OCI digest.")
    parser.add_argument("--catalog", type=Path, default=Path("catalog/approved.json"))
    parser.add_argument("--id", dest="logical_id", required=True)
    parser.add_argument("--cache-root", type=Path, required=True)
    parser.add_argument("--oras", default="oras")
    args = parser.parse_args()
    hydrate(args.catalog, args.logical_id, args.cache_root, args.oras)


if __name__ == "__main__":
    main()
