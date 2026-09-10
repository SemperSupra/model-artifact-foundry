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

import jsonschema

import validate_siglip2 as qualifier

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DECL = REPO_ROOT / "sources" / "siglip2-base-patch16-224.json"
CANDIDATE_SCHEMA = REPO_ROOT / "schemas" / "candidate-manifest.schema.json"
LOGICAL_ID = "embed/siglip2/base-patch16-224"
REVISION = "75de2d55ec2d0b4efc50b3e9ad70dba96a7b2fa2"
HF_REPO = "google/siglip2-base-patch16-224"
EXPECTED_FILES = tuple(qualifier.EXPECTED_FILES)


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
        tf.extractall(dest)


def verify_model_files(model_dir: Path, files: list[dict]) -> None:
    expected = {entry["path"]: entry for entry in files}
    actual = sorted(p.name for p in model_dir.iterdir() if p.is_file())
    if actual != sorted(expected):
        raise RuntimeError(f"model directory file set mismatch: {actual}")
    for name, entry in expected.items():
        path = model_dir / name
        if path.stat().st_size != entry["size_bytes"]:
            raise RuntimeError(f"size mismatch for {name}")
        if sha256_file(path) != entry["sha256"]:
            raise RuntimeError(f"sha256 mismatch for {name}")


def smoke_model_dir(model_dir: Path) -> dict:
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    import PIL
    import PIL.Image
    import torch
    import transformers
    from transformers import AutoModel, AutoProcessor

    model = AutoModel.from_pretrained(str(model_dir), local_files_only=True, trust_remote_code=False)
    processor = AutoProcessor.from_pretrained(str(model_dir), local_files_only=True, trust_remote_code=False)
    img = PIL.Image.new("RGB", (100, 100), color=(128, 64, 200))
    texts = ["a photo of a cat", "a photo of a dog", "synthetic test image"]
    inputs = processor(text=texts, images=img, return_tensors="pt", padding=True)
    with torch.no_grad():
        outputs = model(**inputs)
        image_embeds = outputs.image_embeds if hasattr(outputs, "image_embeds") else model.get_image_features(inputs["pixel_values"])
        text_embeds = outputs.text_embeds if hasattr(outputs, "text_embeds") else model.get_text_features(inputs["input_ids"])

    result = {
        "image_embeddings_shape": list(image_embeds.shape),
        "text_embeddings_shape": list(text_embeds.shape),
        "image_embeddings_finite": bool(torch.isfinite(image_embeds).all().item()),
        "text_embeddings_finite": bool(torch.isfinite(text_embeds).all().item()),
        "torch": torch.__version__,
        "transformers": transformers.__version__,
        "pillow": PIL.__version__,
        "trust_remote_code": False,
        "local_files_only": True,
    }
    if result["image_embeddings_shape"] != [1, 768] or result["text_embeddings_shape"] != [3, 768]:
        raise RuntimeError(f"unexpected embedding shape: {result}")
    if not result["image_embeddings_finite"] or not result["text_embeddings_finite"]:
        raise RuntimeError("non-finite embeddings")
    return result


def prepare(dist_dir: Path, cache_dir: Path) -> None:
    declaration = json.loads(SOURCE_DECL.read_text(encoding="utf-8"))
    if declaration["logical_id"] != LOGICAL_ID or declaration["source"]["discovery_ref"] != REVISION:
        raise RuntimeError("source declaration identity/revision mismatch")
    if sorted(declaration["artifact"]["expected_file_patterns"]) != sorted(EXPECTED_FILES):
        raise RuntimeError("source declaration expected-file allowlist changed")

    evidence = qualifier.run_local_qualification(cache_dir, command_str="python3 tools/harvest_siglip2.py prepare")
    if evidence.get("terminal_state") != "PASS_LOCAL_CANDIDATE":
        raise RuntimeError(f"local qualification did not pass: {evidence}")

    model_dir = cache_dir / HF_REPO / REVISION
    verify_model_files(model_dir, evidence["files"])

    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    dist_dir.mkdir(parents=True)
    archive = dist_dir / "model.tar.gz"
    deterministic_tar_gz(model_dir, archive)

    smoke = smoke_model_dir(model_dir)
    bundle = {
        "schema_version": 1,
        "logical_id": LOGICAL_ID,
        "upstream": {"provider": "huggingface", "repository": HF_REPO, "exact_revision": REVISION},
        "license": {
            "observed_spdx_id": "Apache-2.0",
            "redistribution_verified": True,
            "evidence": evidence["upstream"]["evidence_urls"],
        },
        "format": {"family": "embed/siglip2", "format": "safetensors"},
        "files": [{k: entry[k] for k in ("path", "size_bytes", "sha256")} for entry in evidence["files"]],
        "archive": {"path": "model.tar.gz", "size_bytes": archive.stat().st_size, "sha256": sha256_file(archive)},
        "validation": {
            "profile": "siglip2-local-smoke-v1",
            "status": "passed",
            "claims": [
                "exact declared upstream revision reacquired",
                "declared file set and hashes verified",
                "model and processor load offline with trust_remote_code disabled",
                "image/text embeddings have expected finite 768-dimensional shapes",
            ],
            "framework_versions": {k: smoke[k] for k in ("torch", "transformers", "pillow")},
            "smoke": smoke,
        },
    }
    (dist_dir / "bundle-manifest.json").write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (dist_dir / "NOTICE.txt").write_text(
        "Model Artifact Foundry SigLIP2 candidate bundle\n"
        f"Logical artifact: {LOGICAL_ID}\n"
        f"Source: https://huggingface.co/{HF_REPO}\n"
        f"Exact revision: {REVISION}\n"
        "Observed source license metadata: Apache-2.0\n"
        "Candidate publication is not catalog approval.\n",
        encoding="utf-8",
    )
    print(json.dumps({"terminal_state": "PASS_PREPARE", "logical_id": LOGICAL_ID, "archive_sha256": bundle["archive"]["sha256"]}))


def verify_pulled(bundle_dir: Path) -> None:
    required = {"model.tar.gz", "bundle-manifest.json", "NOTICE.txt"}
    actual = {p.name for p in bundle_dir.iterdir() if p.is_file()}
    if actual != required:
        raise RuntimeError(f"pulled OCI layer set mismatch: {sorted(actual)}")
    bundle = json.loads((bundle_dir / "bundle-manifest.json").read_text(encoding="utf-8"))
    if bundle["logical_id"] != LOGICAL_ID or bundle["upstream"]["exact_revision"] != REVISION:
        raise RuntimeError("pulled bundle identity mismatch")
    archive = bundle_dir / "model.tar.gz"
    if sha256_file(archive) != bundle["archive"]["sha256"]:
        raise RuntimeError("pulled archive hash mismatch")
    with tempfile.TemporaryDirectory(prefix="foundry-siglip2-verify-") as td:
        model_dir = Path(td) / "model"
        model_dir.mkdir()
        safe_extract(archive, model_dir)
        verify_model_files(model_dir, bundle["files"])
        smoke_model_dir(model_dir)
    print(json.dumps({"terminal_state": "PASS_PULLBACK", "logical_id": LOGICAL_ID, "archive_sha256": bundle["archive"]["sha256"]}))


def candidate_manifest(dist_dir: Path, oci_repository: str, digest: str, tool_revision: str, output: Path) -> None:
    if not digest.startswith("sha256:") or len(digest) != 71:
        raise RuntimeError("invalid OCI digest")
    bundle = json.loads((dist_dir / "bundle-manifest.json").read_text(encoding="utf-8"))
    manifest = {
        "schema_version": 1,
        "logical_id": LOGICAL_ID,
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
            {"component": "transformers", "constraint": f"validated == {bundle['validation']['framework_versions']['transformers']}", "evidence": "siglip2-local-smoke-v1"},
            {"component": "torch", "constraint": f"validated == {bundle['validation']['framework_versions']['torch']}", "evidence": "siglip2-local-smoke-v1"},
        ],
        "oci": {"repository": oci_repository, "digest": digest, "pullback_verified": True},
    }
    schema = json.loads(CANDIDATE_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(manifest, schema)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def temporary_catalog(candidate_path: Path, output: Path) -> None:
    c = json.loads(candidate_path.read_text(encoding="utf-8"))
    # Test-only selector for exercising the generic hydrator. This file is ephemeral and is not promotion authority.
    doc = {
        "schema_version": 1,
        "artifacts": {
            LOGICAL_ID: {
                "oci_repository": c["oci"]["repository"],
                "approved_digest": c["oci"]["digest"],
                "candidate_evidence": {"repository": "CI-EPHEMERAL", "commit_sha": c["validation"]["tool_revision"], "manifest_path": str(candidate_path)},
                "upstream_exact_revision": REVISION,
                "license_spdx_id": "Apache-2.0",
                "approved_at": c["acquired_at"],
                "compatibility": [{"component": x["component"], "constraint": x["constraint"]} for x in c.get("compatibility", [])],
            }
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("prepare")
    p.add_argument("--dist-dir", type=Path, default=Path("dist"))
    p.add_argument("--cache-dir", type=Path, default=Path("/tmp/siglip2-cache"))

    p = sub.add_parser("verify-pulled")
    p.add_argument("--bundle-dir", type=Path, required=True)

    p = sub.add_parser("smoke-model")
    p.add_argument("--model-dir", type=Path, required=True)

    p = sub.add_parser("candidate-manifest")
    p.add_argument("--dist-dir", type=Path, default=Path("dist"))
    p.add_argument("--oci-repository", required=True)
    p.add_argument("--digest", required=True)
    p.add_argument("--tool-revision", required=True)
    p.add_argument("--output", type=Path, required=True)

    p = sub.add_parser("temporary-catalog")
    p.add_argument("--candidate", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)

    args = parser.parse_args()
    if args.cmd == "prepare":
        prepare(args.dist_dir, args.cache_dir)
    elif args.cmd == "verify-pulled":
        verify_pulled(args.bundle_dir)
    elif args.cmd == "smoke-model":
        print(json.dumps(smoke_model_dir(args.model_dir)))
    elif args.cmd == "candidate-manifest":
        candidate_manifest(args.dist_dir, args.oci_repository, args.digest, args.tool_revision, args.output)
    else:
        temporary_catalog(args.candidate, args.output)


if __name__ == "__main__":
    main()
