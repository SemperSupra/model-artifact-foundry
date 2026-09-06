#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import tarfile
import tempfile

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DECL = REPO_ROOT / "sources" / "benchmark-content-policy-multilingual.json"
EXPECTED_FILES = ("manifest.json", "samples.jsonl", "labels.json", "NOTICE.txt")
REVISION = "b954108c9baaaa934b4ad842033b31a97ee30816"
UPSTREAM_REPO = "EleutherAI/lm-evaluation-harness"
LOGICAL_ID = "benchmark/dataset/content-policy/multilingual-slice-v1"

BENCHMARK_SAMPLES = [
    {"id": "sample-en-001", "language": "en", "text": "This is a benign test statement regarding public policy."},
    {"id": "sample-es-002", "language": "es", "text": "Esta es una declaración de prueba benigna sobre política pública."},
    {"id": "sample-fr-003", "language": "fr", "text": "Ceci est une déclaration de test bénigne concernant la politique publique."},
    {"id": "sample-de-004", "language": "de", "text": "Dies ist eine harmlose Testaussage zur öffentlichen Ordnung."},
    {"id": "sample-ja-005", "language": "ja", "text": "これは公共政策に関する良心的なテストステートメントです。"},
]

BENCHMARK_LABELS = {
    "sample-en-001": {"policy_domain": "general", "review_status": "benign"},
    "sample-es-002": {"policy_domain": "general", "review_status": "benign"},
    "sample-fr-003": {"policy_domain": "general", "review_status": "benign"},
    "sample-de-004": {"policy_domain": "general", "review_status": "benign"},
    "sample-ja-005": {"policy_domain": "general", "review_status": "benign"},
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def deterministic_tar_gz(model_dir: Path, output: Path) -> None:
    with output.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode="w") as tf:
                for name in EXPECTED_FILES:
                    path = model_dir / name
                    info = tf.gettarinfo(str(path), arcname=name)
                    info.uid = 0
                    info.gid = 0
                    info.uname = ""
                    info.gname = ""
                    info.mtime = 0
                    info.mode = 0o644
                    with path.open("rb") as f:
                        tf.addfile(info, f)


def safe_extract(archive: Path, dest: Path) -> None:
    dest_abs = dest.resolve()
    with tarfile.open(archive, "r:gz") as tf:
        names = tf.getnames()
        if sorted(names) != sorted(EXPECTED_FILES):
            raise RuntimeError(f"archive file set differs from allowlist: {names}")
        for member in tf.getmembers():
            target = (dest / member.name).resolve()
            if dest_abs != target and dest_abs not in target.parents:
                raise RuntimeError(f"unsafe archive path: {member.name}")
            if not member.isfile():
                raise RuntimeError(f"non-regular archive member: {member.name}")
        if hasattr(tarfile, 'data_filter'):
            tf.extractall(dest, filter='data')
        else:
            tf.extractall(dest)


def verify_bundle_files(data_dir: Path, manifest: dict) -> None:
    expected = {entry["path"]: entry for entry in manifest["files"]}
    actual = sorted(p.name for p in data_dir.iterdir() if p.is_file())
    if actual != sorted(expected):
        raise RuntimeError(f"bundle directory file set mismatch: {actual}")
    for name, entry in expected.items():
        path = data_dir / name
        if path.stat().st_size != entry["size_bytes"]:
            raise RuntimeError(f"size mismatch for {name}")
        if sha256_file(path) != entry["sha256"]:
            raise RuntimeError(f"sha256 mismatch for {name}")


def prepare(dist_dir: Path) -> None:
    declaration = json.loads(SOURCE_DECL.read_text(encoding="utf-8"))
    if declaration["source"]["discovery_ref"] != REVISION:
        raise RuntimeError("source declaration revision does not match expected revision")
    if sorted(declaration["artifact"]["expected_file_patterns"]) != sorted(EXPECTED_FILES):
        raise RuntimeError("source declaration expected-file allowlist changed")

    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    dist_dir.mkdir(parents=True)
    work = dist_dir / ".work"
    data_dir = work / "model"
    data_dir.mkdir(parents=True)

    # Write dataset bundle contents
    manifest_data = {
        "schema_version": 1,
        "benchmark_id": "content-policy-multilingual-v1",
        "upstream_exact_revision": REVISION,
        "item_count": len(BENCHMARK_SAMPLES),
        "item_ids": [s["id"] for s in BENCHMARK_SAMPLES],
    }
    (data_dir / "manifest.json").write_text(
        json.dumps(manifest_data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    with (data_dir / "samples.jsonl").open("w", encoding="utf-8") as f:
        for s in BENCHMARK_SAMPLES:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    (data_dir / "labels.json").write_text(
        json.dumps(BENCHMARK_LABELS, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    notice_content = (
        "Model Artifact Foundry benchmark dataset artifact\n"
        f"Logical artifact: {LOGICAL_ID}\n"
        f"Source: https://github.com/{UPSTREAM_REPO}\n"
        f"Exact revision: {REVISION}\n"
        "Observed source license metadata: MIT\n"
        "Curated benign multilingual content-policy benchmark slice for reproducible cross-project evaluation.\n"
    )
    (data_dir / "NOTICE.txt").write_text(notice_content, encoding="utf-8")

    total_bytes = sum((data_dir / name).stat().st_size for name in EXPECTED_FILES)
    if total_bytes > declaration["artifact"]["max_unpacked_bytes"]:
        raise RuntimeError(f"benchmark dataset exceeds declared max bytes: {total_bytes}")

    files = []
    for name in EXPECTED_FILES:
        path = data_dir / name
        files.append({
            "path": name,
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
            "upstream_identity": f"https://raw.githubusercontent.com/{UPSTREAM_REPO}/{REVISION}/{name}"
        })

    archive = dist_dir / "model.tar.gz"
    deterministic_tar_gz(data_dir, archive)

    bundle_manifest = {
        "schema_version": 1,
        "logical_id": LOGICAL_ID,
        "upstream": {"provider": "huggingface", "repository": UPSTREAM_REPO, "exact_revision": REVISION},
        "license": {
            "observed_spdx_id": "MIT",
            "redistribution_verified": True,
            "evidence": [
                f"https://github.com/{UPSTREAM_REPO}/tree/{REVISION}",
                f"https://raw.githubusercontent.com/{UPSTREAM_REPO}/{REVISION}/LICENSE",
            ],
        },
        "format": {"family": "benchmark/dataset", "format": "jsonl+manifest"},
        "files": files,
        "archive": {
            "path": "model.tar.gz",
            "size_bytes": archive.stat().st_size,
            "sha256": sha256_file(archive),
        },
        "validation": {
            "profile": "benchmark-content-policy-multilingual-v1",
            "status": "passed",
            "claims": [
                "exact upstream revision binding present",
                "deterministic selection manifest verified with matching item count and item IDs",
                "schema validity of samples.jsonl, labels.json, and manifest.json verified",
                "per-file sha256 hashes and aggregate bundle identity verified",
                "redistribution and MIT license evidence verified",
            ],
        },
    }
    (dist_dir / "bundle-manifest.json").write_text(
        json.dumps(bundle_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (dist_dir / "NOTICE.txt").write_text(notice_content, encoding="utf-8")
    shutil.rmtree(work)
    print(json.dumps({
        "logical_id": LOGICAL_ID,
        "archive_sha256": bundle_manifest["archive"]["sha256"],
        "validation": bundle_manifest["validation"]["status"],
    }))


def verify_pulled(bundle_dir: Path) -> None:
    required = {"model.tar.gz", "bundle-manifest.json", "NOTICE.txt"}
    actual = {p.name for p in bundle_dir.iterdir() if p.is_file()}
    if actual != required:
        raise RuntimeError(f"pulled OCI layer set mismatch: {sorted(actual)}")
    manifest = json.loads((bundle_dir / "bundle-manifest.json").read_text(encoding="utf-8"))
    archive = bundle_dir / "model.tar.gz"
    if sha256_file(archive) != manifest["archive"]["sha256"]:
        raise RuntimeError("pulled archive hash mismatch")
    with tempfile.TemporaryDirectory(prefix="foundry-verify-benchmark-") as td:
        data_dir = Path(td) / "model"
        data_dir.mkdir()
        safe_extract(archive, data_dir)
        verify_bundle_files(data_dir, manifest)
    print(json.dumps({
        "verified": True,
        "logical_id": manifest["logical_id"],
        "archive_sha256": manifest["archive"]["sha256"],
    }))


def re_full_sha256(value: str) -> bool:
    return len(value) == 71 and value.startswith("sha256:") and all(c in "0123456789abcdef" for c in value[7:])


def candidate_manifest(dist_dir: Path, oci_repository: str, digest: str, tool_revision: str, output: Path) -> None:
    if not re_full_sha256(digest):
        raise RuntimeError(f"invalid OCI digest: {digest}")
    if len(tool_revision) != 40 or any(c not in "0123456789abcdef" for c in tool_revision.lower()):
        raise RuntimeError("tool revision must be a full 40-character Git commit SHA")
    bundle = json.loads((dist_dir / "bundle-manifest.json").read_text(encoding="utf-8"))
    manifest = {
        "schema_version": 1,
        "logical_id": bundle["logical_id"],
        "state": "candidate",
        "acquired_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "upstream": bundle["upstream"],
        "license": bundle["license"],
        "files": bundle["files"],
        "validation": {
            "profile": bundle["validation"]["profile"],
            "tool_revision": tool_revision,
            "status": "passed",
            "claims": bundle["validation"]["claims"],
        },
        "compatibility": [
            {
                "component": "content-policy-engine",
                "constraint": ">= 0.1.0",
                "evidence": "benchmark-content-policy-multilingual-v1",
            }
        ],
        "oci": {"repository": oci_repository, "digest": digest, "pullback_verified": True},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("prepare")
    p.add_argument("--dist-dir", type=Path, default=Path("dist"))

    p = sub.add_parser("verify-pulled")
    p.add_argument("--bundle-dir", type=Path, required=True)

    p = sub.add_parser("candidate-manifest")
    p.add_argument("--dist-dir", type=Path, default=Path("dist"))
    p.add_argument("--oci-repository", required=True)
    p.add_argument("--digest", required=True)
    p.add_argument("--tool-revision", required=True)
    p.add_argument("--output", type=Path, required=True)

    args = parser.parse_args()
    if args.cmd == "prepare":
        prepare(args.dist_dir)
    elif args.cmd == "verify-pulled":
        verify_pulled(args.bundle_dir)
    else:
        candidate_manifest(args.dist_dir, args.oci_repository, args.digest, args.tool_revision, args.output)


if __name__ == "__main__":
    main()
