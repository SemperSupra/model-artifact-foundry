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
import urllib.request

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DECL = REPO_ROOT / "sources" / "ms-marco-minilm-l6-v2-reranker.json"
SOURCE_SCHEMA = REPO_ROOT / "schemas" / "source-declaration.schema.json"
CANDIDATE_SCHEMA = REPO_ROOT / "schemas" / "candidate-manifest.schema.json"
LOGICAL_ID = "rerank/cross-encoder/ms-marco-minilm-l6-v2"
HF_REPO = "cross-encoder/ms-marco-MiniLM-L6-v2"
REVISION = "233902d25c440f23af6f7d6e94d2946bac0bee0a"
HF_API = f"https://huggingface.co/api/models/{HF_REPO}"
EXPECTED_FILES = (
    "config.json",
    "model.safetensors",
    "special_tokens_map.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "vocab.txt",
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "SemperSupra-model-artifact-foundry/1"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def download(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "SemperSupra-model-artifact-foundry/1"})
    with urllib.request.urlopen(req, timeout=300) as resp, dest.open("wb") as out:
        shutil.copyfileobj(resp, out)


def validate_declaration() -> dict:
    declaration = json.loads(SOURCE_DECL.read_text(encoding="utf-8"))
    schema = json.loads(SOURCE_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(declaration, schema)
    if declaration["logical_id"] != LOGICAL_ID:
        raise RuntimeError("source declaration logical ID mismatch")
    if declaration["source"]["repository"] != HF_REPO or declaration["source"]["discovery_ref"] != REVISION:
        raise RuntimeError("source declaration repository/revision mismatch")
    if sorted(declaration["artifact"]["expected_file_patterns"]) != sorted(EXPECTED_FILES):
        raise RuntimeError("source declaration expected-file allowlist mismatch")
    return declaration


def validate_upstream_metadata(meta: dict) -> dict:
    if meta.get("id") != HF_REPO:
        raise RuntimeError(f"unexpected upstream id: {meta.get('id')!r}")
    if meta.get("sha") != REVISION:
        raise RuntimeError(f"upstream main moved: expected {REVISION}, observed {meta.get('sha')}; do not silently substitute")
    if meta.get("private"):
        raise RuntimeError("upstream unexpectedly private")
    if meta.get("gated") not in (False, None):
        raise RuntimeError(f"upstream unexpectedly gated: {meta.get('gated')!r}")
    if meta.get("disabled"):
        raise RuntimeError("upstream disabled")
    license_id = str((meta.get("cardData") or {}).get("license") or "").upper()
    if license_id != "APACHE-2.0":
        raise RuntimeError(f"expected Apache-2.0 metadata, observed {license_id!r}")
    siblings = {x.get("rfilename") for x in meta.get("siblings", [])}
    missing = set(EXPECTED_FILES) - siblings
    if missing:
        raise RuntimeError(f"upstream missing expected files: {sorted(missing)}")
    return {
        "id": meta["id"],
        "sha": meta["sha"],
        "license": license_id,
        "private": bool(meta.get("private")),
        "gated": meta.get("gated"),
        "disabled": bool(meta.get("disabled")),
    }


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
    import torch
    import transformers
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    torch.manual_seed(0)
    tokenizer = AutoTokenizer.from_pretrained(str(model_dir), local_files_only=True, trust_remote_code=False)
    model = AutoModelForSequenceClassification.from_pretrained(str(model_dir), local_files_only=True, trust_remote_code=False)
    model.eval()

    query = "Which planet is known as the Red Planet?"
    passages = [
        "Venus is often called Earth's twin because of its similar size and proximity.",
        "Mars, known for its reddish appearance, is often referred to as the Red Planet.",
        "Jupiter, the largest planet in our solar system, has a prominent red spot.",
        "Saturn, famous for its rings, is sometimes mistaken for the Red Planet.",
    ]
    inputs = tokenizer([query] * len(passages), passages, padding=True, truncation=True, max_length=128, return_tensors="pt")
    with torch.inference_mode():
        out1 = model(**inputs, output_hidden_states=True, return_dict=True)
        out2 = model(**inputs, return_dict=True)
    scores1 = out1.logits.reshape(-1).float().cpu()
    scores2 = out2.logits.reshape(-1).float().cpu()
    if scores1.shape != (4,):
        raise RuntimeError(f"unexpected score shape: {tuple(scores1.shape)}")
    if not torch.isfinite(scores1).all().item():
        raise RuntimeError("non-finite reranker scores")
    max_repeat_delta = float((scores1 - scores2).abs().max().item())
    if max_repeat_delta > 1e-6:
        raise RuntimeError(f"repeat score drift exceeded deterministic smoke tolerance: {max_repeat_delta}")
    top_index = int(torch.argmax(scores1).item())
    if top_index != 1:
        raise RuntimeError(f"semantic ranking smoke failed: expected Mars passage at index 1, observed {top_index}; scores={scores1.tolist()}")
    hidden_states = out1.hidden_states
    if not hidden_states or len(hidden_states) < 2:
        raise RuntimeError("hidden-state observability unavailable")
    if not torch.isfinite(hidden_states[-1]).all().item():
        raise RuntimeError("non-finite final hidden state")

    return {
        "score_shape": list(scores1.shape),
        "scores": [float(x) for x in scores1.tolist()],
        "top_index": top_index,
        "repeat_max_abs_delta": max_repeat_delta,
        "hidden_state_layers": len(hidden_states),
        "hidden_size": int(hidden_states[-1].shape[-1]),
        "torch": torch.__version__,
        "transformers": transformers.__version__,
        "trust_remote_code": False,
        "local_files_only": True,
    }


def prepare(dist_dir: Path, cache_dir: Path) -> None:
    declaration = validate_declaration()
    source_meta = validate_upstream_metadata(fetch_json(HF_API))
    model_dir = cache_dir / "model"
    model_dir.mkdir(parents=True, exist_ok=True)

    files = []
    total = 0
    for name in EXPECTED_FILES:
        dest = model_dir / name
        if not dest.exists():
            download(f"https://huggingface.co/{HF_REPO}/resolve/{REVISION}/{name}?download=true", dest)
        size = dest.stat().st_size
        total += size
        files.append({"path": name, "size_bytes": size, "sha256": sha256_file(dest)})
    if total > declaration["artifact"]["max_unpacked_bytes"]:
        raise RuntimeError(f"model exceeds declared max bytes: {total}")
    verify_model_files(model_dir, files)
    smoke = smoke_model_dir(model_dir)

    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    dist_dir.mkdir(parents=True)
    archive = dist_dir / "model.tar.gz"
    deterministic_tar_gz(model_dir, archive)

    bundle = {
        "schema_version": 1,
        "logical_id": LOGICAL_ID,
        "upstream": {"provider": "huggingface", "repository": HF_REPO, "exact_revision": REVISION},
        "license": {
            "observed_spdx_id": "Apache-2.0",
            "redistribution_verified": True,
            "evidence": [f"https://huggingface.co/{HF_REPO}/tree/{REVISION}", HF_API],
        },
        "format": {"family": "rerank/cross-encoder", "format": "safetensors"},
        "files": files,
        "archive": {"path": "model.tar.gz", "size_bytes": archive.stat().st_size, "sha256": sha256_file(archive)},
        "validation": {
            "profile": "cross-encoder-msmarco-ranking-smoke-v1",
            "status": "passed",
            "claims": [
                "exact declared upstream revision reacquired and allow-listed file hashes recorded",
                "model and tokenizer load offline with trust_remote_code disabled",
                "sequence-classification output is one finite scalar per query/passage pair",
                "repeated deterministic inference is stable within 1e-6 max absolute score delta",
                "the model-card Red Planet smoke ranks the Mars passage above three distractors",
                "hidden-state observability is available for later Model Spelunker representation probes",
            ],
            "framework_versions": {"torch": smoke["torch"], "transformers": smoke["transformers"]},
            "smoke": smoke,
            "source_metadata": source_meta,
        },
    }
    (dist_dir / "bundle-manifest.json").write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (dist_dir / "NOTICE.txt").write_text(
        "Model Artifact Foundry MiniLM reranker candidate bundle\n"
        f"Logical artifact: {LOGICAL_ID}\n"
        f"Source: https://huggingface.co/{HF_REPO}\n"
        f"Exact revision: {REVISION}\n"
        "Observed source license metadata: Apache-2.0\n"
        "Candidate publication is not catalog approval.\n",
        encoding="utf-8",
    )
    print(json.dumps({"terminal_state": "PASS_PREPARE", "logical_id": LOGICAL_ID, "archive_sha256": bundle["archive"]["sha256"], "smoke": smoke}))


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
    with tempfile.TemporaryDirectory(prefix="foundry-reranker-verify-") as td:
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
            {"component": "transformers", "constraint": f"validated == {bundle['validation']['framework_versions']['transformers']}", "evidence": "cross-encoder-msmarco-ranking-smoke-v1"},
            {"component": "torch", "constraint": f"validated == {bundle['validation']['framework_versions']['torch']}", "evidence": "cross-encoder-msmarco-ranking-smoke-v1"},
        ],
        "oci": {"repository": oci_repository, "digest": digest, "pullback_verified": True},
    }
    jsonschema.validate(manifest, json.loads(CANDIDATE_SCHEMA.read_text(encoding="utf-8")))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def temporary_catalog(candidate_path: Path, output: Path) -> None:
    c = json.loads(candidate_path.read_text(encoding="utf-8"))
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
    p.add_argument("--cache-dir", type=Path, default=Path("/tmp/msmarco-minilm-reranker-cache"))

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
