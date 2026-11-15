#!/usr/bin/env python3
"""Source-locked MakeHuman ZIP -> disposable staging -> existing MAF verifier.

Research bridge only. No content-manifest adoption, approved catalog, registry
write, Drive custody, runtime installation, arbitrary upstream execution, or
model/character quality claims. The imported generic hydrator is pinned by CI
to a specific reviewed PR revision.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

OBSERVED_SOURCE_SHA = "f61f4f36bb4fe43486efa2a644eea9d6760e510bde10eecc97a4ddf28424e4d3"
PINNED_HYDRATOR_COMMIT = "8f14e4179e9333ebf2eef2c26c7e74a3bc5608f1"


def fail(message: str) -> None:
    raise RuntimeError(message)


def load_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        fail("invalid provenance record")
    return data


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def run(fetch_path: Path, stage_path: Path, verifier_path: Path, base: Path, output: Path) -> dict:
    fetched = load_json(fetch_path)
    staged = load_json(stage_path)
    if fetched.get("status") != "STAGED_VERIFIED_NOT_ADOPTED" or staged.get("status") != "STAGED_EPHEMERAL_NOT_ADOPTED":
        fail("not an explicitly unadopted research input")
    if fetched.get("archive_sha256") != OBSERVED_SOURCE_SHA or staged.get("archive_sha256") != OBSERVED_SOURCE_SHA:
        fail("different or unapproved observed research archive bytes")
    if fetched.get("member_count") != 23 or staged.get("member_count") != 23:
        fail("source member set changed")
    if fetched.get("total_unpacked_bytes") != 751956 or staged.get("total_unpacked_bytes") != 751956:
        fail("source unpacked size changed")
    base = base.resolve(strict=True)
    staging_parent = base / "stage"
    root = Path(staged["staging_root"])
    if root.is_symlink() or root.resolve(strict=True).parent != staging_parent.resolve(strict=True):
        fail("staging root not inside expected disposable workspace")
    if verifier_path.is_symlink() or not verifier_path.is_file():
        fail("missing pinned generic MAF verification module")
    spec = importlib.util.spec_from_file_location("maf_pinned_hydrator", verifier_path)
    if spec is None or spec.loader is None:
        fail("unable to load source-pinned generic verifier")
    verifier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verifier)

    # Research-only manifest is created from staged bytes, rather than being
    # falsely attributed to the publisher or to the Foundry approved catalog.
    files = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            fail("stage contains symlink")
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        files.append({"path": relative, "size_bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {"files": files}
    if len(files) != 23 or sum(row["size_bytes"] for row in files) != 751956:
        fail("staged data inventory diverges")
    verifier.verify_model_dir(root, manifest)

    # Independent negative controls exercise the candidate hydrated bytes.
    # Exact-length byte corruption must fail the hash check, not the size check.
    target = root / files[0]["path"]
    original = target.read_bytes()
    if not original:
        fail("first staged fixture unexpectedly empty")
    changed = bytes([original[0] ^ 0x01]) + original[1:]
    try:
        target.write_bytes(changed)
        try:
            verifier.verify_model_dir(root, manifest)
        except RuntimeError as exc:
            if "hash mismatch" not in str(exc):
                raise AssertionError("incorrect hash-negative oracle") from exc
        else:
            fail("same-size corrupted bytes passed verification")
    finally:
        target.write_bytes(original)
    verifier.verify_model_dir(root, manifest)

    # Symlinked contents must remain forbidden even if they refer to byte-equal
    # files. This test changes only disposable source staging.
    try:
        target.unlink()
        os.symlink(files[1]["path"], target)
        try:
            verifier.verify_model_dir(root, manifest)
        except RuntimeError as exc:
            if "symlinked" not in str(exc):
                raise AssertionError("incorrect symlink-negative oracle") from exc
        else:
            fail("symlinked source bytes accepted")
    finally:
        if target.exists() or target.is_symlink():
            target.unlink()
        target.write_bytes(original)
    verifier.verify_model_dir(root, manifest)

    # Never copy source bytes to the output receipt.
    receipt = {
        "schema": "maf.makehuman.source-stage-generic-hydration/v0.1",
        "status": "EPHEMERAL_VERIFIED_NOT_ADOPTED",
        "source_url": fetched.get("source_url"),
        "source_sha256": OBSERVED_SOURCE_SHA,
        "source_sha_authority": "prior_public_runner_observation_not_publisher_signature",
        "hydrator_source_commit": PINNED_HYDRATOR_COMMIT,
        "hydrator_source_sha256": sha256_file(verifier_path),
        "member_count": len(files),
        "total_unpacked_bytes": sum(row["size_bytes"] for row in files),
        "evidence": {
            "real_verified_source_download": True,
            "verified_disposable_stage": True,
            "generic_nested_hydrator_checksum_validation": True,
            "same_size_tamper_detected": True,
            "symlinked_member_rejected": True,
        },
        "unqualified": [
            "independent_upstream_signed_provenance",
            "legal_license_rights_admission",
            "approved_content_manifest_or_OCI_catalog",
            "durable_cache_hydration_or_Drive_AAR_CDR",
            "makehuman_morph_rig_animation_character_compatibility",
            "cross-platform_live_HIL",
        ],
    }
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--fetch", type=Path, required=True)
    p.add_argument("--stage", type=Path, required=True)
    p.add_argument("--verifier", type=Path, required=True)
    p.add_argument("--workspace", type=Path, required=True)
    p.add_argument("--receipt", type=Path, required=True)
    args = p.parse_args()
    r = run(args.fetch, args.stage, args.verifier, args.workspace, args.receipt)
    print("MAF_MH_GENERIC_HYDRATION_BRIDGE_RECEIPT", json.dumps(r, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, AssertionError, RuntimeError) as exc:
        print("MAF_MH_GENERIC_HYDRATION_BRIDGE_REJECTED", type(exc).__name__, str(exc), file=sys.stderr)
        sys.exit(3)
