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


def atomic_write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    tmp.write_text(value, encoding="utf-8")
    os.replace(tmp, path)


def atomic_write_json(path: Path, value: dict) -> None:
    atomic_write_text(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def update_selection(cache_root: Path, logical_id: str, digest: str, model_dir: Path) -> None:
    atomic_write_json(
        cache_root / "selected" / f"{safe_name(logical_id)}.json",
        {"schema_version": 1, "logical_id": logical_id, "digest": digest, "model_dir": str(model_dir)},
    )


def hf_repo_folder(repo_id: str) -> str:
    parts = repo_id.split("/")
    if len(parts) != 2 or not all(parts):
        raise RuntimeError(f"Hugging Face repo id must be namespace/name: {repo_id!r}")
    return "models--" + "--".join(parts)


def materialize_hf_cache_projection(
    cache_root: Path,
    repo_id: str,
    ref_name: str,
    revision: str,
    model_dir: Path,
    manifest: dict,
) -> Path:
    """Create a replaceable Hugging Face cache view backed by the Foundry blob.

    The Foundry content-addressed blob remains authoritative. This projection exists only
    for consumers such as Faster Whisper that resolve a model name through Hugging Face's
    documented refs/snapshots/trees cache structure.
    """
    if len(revision) != 40 or any(c not in "0123456789abcdef" for c in revision.lower()):
        raise RuntimeError(f"Hugging Face compatibility revision must be a full commit SHA: {revision!r}")
    if not ref_name or "/" in ref_name or ref_name in {".", ".."}:
        raise RuntimeError(f"unsafe Hugging Face ref name: {ref_name!r}")

    storage = cache_root / hf_repo_folder(repo_id)
    snapshots = storage / "snapshots"
    snapshot = snapshots / revision
    expected = {entry["path"]: entry for entry in manifest["files"]}

    projection_valid = snapshot.is_dir()
    if projection_valid:
        try:
            for name, entry in expected.items():
                projected = snapshot / name
                if not projected.exists() or projected.stat().st_size != entry["size_bytes"]:
                    projection_valid = False
                    break
                if sha256_file(projected) != entry["sha256"]:
                    projection_valid = False
                    break
        except OSError:
            projection_valid = False

    if not projection_valid:
        snapshots.mkdir(parents=True, exist_ok=True)
        tmp_snapshot = snapshots / f".{revision}.{uuid.uuid4().hex}.tmp"
        tmp_snapshot.mkdir()
        try:
            for name in sorted(expected):
                source = (model_dir / name).resolve()
                target = tmp_snapshot / name
                target.symlink_to(os.path.relpath(source, start=tmp_snapshot))
            if snapshot.exists() or snapshot.is_symlink():
                if snapshot.is_dir() and not snapshot.is_symlink():
                    shutil.rmtree(snapshot)
                else:
                    snapshot.unlink()
            os.replace(tmp_snapshot, snapshot)
        finally:
            if tmp_snapshot.exists():
                shutil.rmtree(tmp_snapshot, ignore_errors=True)

    atomic_write_text(storage / "refs" / ref_name, revision)
    atomic_write_json(
        storage / "trees" / f"{revision}.json",
        {
            "format_version": 1,
            "files": {
                name: {"size": entry["size_bytes"], "blob_id": entry["sha256"]}
                for name, entry in sorted(expected.items())
            },
        },
    )
    return snapshot


def apply_compatibility_projection(
    *,
    cache_root: Path,
    entry: dict,
    model_dir: Path,
    manifest: dict,
    hf_cache_repo: str | None,
    hf_cache_ref: str,
) -> None:
    if hf_cache_repo:
        materialize_hf_cache_projection(
            cache_root,
            hf_cache_repo,
            hf_cache_ref,
            entry["upstream_exact_revision"],
            model_dir,
            manifest,
        )


def hydrate(
    catalog_path: Path,
    logical_id: str,
    cache_root: Path,
    oras: str,
    *,
    hf_cache_repo: str | None = None,
    hf_cache_ref: str = "main",
) -> Path:
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
            apply_compatibility_projection(
                cache_root=cache_root,
                entry=entry,
                model_dir=model_dir,
                manifest=manifest,
                hf_cache_repo=hf_cache_repo,
                hf_cache_ref=hf_cache_ref,
            )
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
        model_dir = final_dir / "model"
        apply_compatibility_projection(
            cache_root=cache_root,
            entry=entry,
            model_dir=model_dir,
            manifest=manifest,
            hf_cache_repo=hf_cache_repo,
            hf_cache_ref=hf_cache_ref,
        )
        update_selection(cache_root, logical_id, digest, model_dir)
        print(model_dir)
        return model_dir
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Hydrate one approved Foundry artifact by immutable OCI digest.")
    parser.add_argument("--catalog", type=Path, default=Path("catalog/approved.json"))
    parser.add_argument("--id", dest="logical_id", required=True)
    parser.add_argument("--cache-root", type=Path, required=True)
    parser.add_argument("--oras", default="oras")
    parser.add_argument(
        "--hf-cache-repo",
        help="Optional namespace/name Hugging Face cache projection for consumers that resolve a model name.",
    )
    parser.add_argument("--hf-cache-ref", default="main")
    args = parser.parse_args()
    hydrate(
        args.catalog,
        args.logical_id,
        args.cache_root,
        args.oras,
        hf_cache_repo=args.hf_cache_repo,
        hf_cache_ref=args.hf_cache_ref,
    )


if __name__ == "__main__":
    main()
