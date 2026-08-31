#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import tarfile
import tempfile
import urllib.request

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DECL = REPO_ROOT / "sources" / "faster-whisper-tiny.json"
EXPECTED_FILES = ("config.json", "model.bin", "tokenizer.json", "vocabulary.txt")
HF_API = "https://huggingface.co/api/models/Systran/faster-whisper-tiny"
HF_REPO = "Systran/faster-whisper-tiny"
REVISION = "d90ca5fe260221311c53c58e660288d3deb8d356"
FIXTURE_COMMIT = "6e3be77e1a105e59086e3e21ff5f609fd6fa89a5"
FIXTURE_URL = f"https://raw.githubusercontent.com/openai/whisper/{FIXTURE_COMMIT}/tests/jfk.flac"
LOGICAL_ID = "asr/faster-whisper/tiny"


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
    with urllib.request.urlopen(req, timeout=180) as resp, dest.open("wb") as out:
        shutil.copyfileobj(resp, out)


def validate_upstream_metadata(meta: dict) -> dict:
    if meta.get("id") != HF_REPO:
        raise RuntimeError(f"unexpected upstream id: {meta.get('id')!r}")
    if meta.get("sha") != REVISION:
        raise RuntimeError(
            f"upstream main moved: expected PoC revision {REVISION}, observed {meta.get('sha')}. "
            "Do not silently substitute a newer revision."
        )
    if meta.get("private"):
        raise RuntimeError("upstream unexpectedly became private")
    if meta.get("gated") not in (False, None):
        raise RuntimeError(f"upstream is gated: {meta.get('gated')!r}")
    if meta.get("disabled"):
        raise RuntimeError("upstream is disabled")
    card = meta.get("cardData") or {}
    license_id = str(card.get("license") or "").upper()
    if license_id != "MIT":
        raise RuntimeError(f"expected MIT source metadata, observed {license_id!r}")
    siblings = {x.get("rfilename") for x in meta.get("siblings", [])}
    missing = set(EXPECTED_FILES) - siblings
    if missing:
        raise RuntimeError(f"upstream metadata missing expected files: {sorted(missing)}")
    return {
        "id": meta["id"],
        "sha": meta["sha"],
        "private": bool(meta.get("private")),
        "gated": meta.get("gated"),
        "disabled": bool(meta.get("disabled")),
        "license": license_id,
        "siblings": sorted(x for x in siblings if x),
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


def verify_model_files(model_dir: Path, manifest: dict) -> None:
    expected = {entry["path"]: entry for entry in manifest["files"]}
    actual = sorted(p.name for p in model_dir.iterdir() if p.is_file())
    if actual != sorted(expected):
        raise RuntimeError(f"model directory file set mismatch: {actual}")
    for name, entry in expected.items():
        path = model_dir / name
        if path.stat().st_size != entry["size_bytes"]:
            raise RuntimeError(f"size mismatch for {name}")
        if sha256_file(path) != entry["sha256"]:
            raise RuntimeError(f"sha256 mismatch for {name}")


def prepare(dist_dir: Path) -> None:
    declaration = json.loads(SOURCE_DECL.read_text(encoding="utf-8"))
    if declaration["source"]["discovery_ref"] != REVISION:
        raise RuntimeError("source declaration revision does not match PoC revision")
    if sorted(declaration["artifact"]["expected_file_patterns"]) != sorted(EXPECTED_FILES):
        raise RuntimeError("source declaration expected-file allowlist changed")

    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    dist_dir.mkdir(parents=True)
    work = dist_dir / ".work"
    model_dir = work / "model"
    model_dir.mkdir(parents=True)

    source_meta = validate_upstream_metadata(fetch_json(HF_API))
    total = 0
    files = []
    for name in EXPECTED_FILES:
        url = f"https://huggingface.co/{HF_REPO}/resolve/{REVISION}/{name}?download=true"
        dest = model_dir / name
        download(url, dest)
        size = dest.stat().st_size
        total += size
        files.append({"path": name, "size_bytes": size, "sha256": sha256_file(dest), "source_url": url})

    if total > declaration["artifact"]["max_unpacked_bytes"]:
        raise RuntimeError(f"model exceeds declared max bytes: {total}")

    fixture = work / "jfk.flac"
    download(FIXTURE_URL, fixture)
    fixture_sha = sha256_file(fixture)

    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    from faster_whisper import WhisperModel

    model = WhisperModel(str(model_dir), device="cpu", compute_type="int8", local_files_only=True)
    segments, info = model.transcribe(str(fixture), language="en", beam_size=1)
    transcript = "".join(seg.text for seg in segments).strip()
    low = transcript.lower()
    for phrase in ("my fellow americans", "your country", "do for you"):
        if phrase not in low:
            raise RuntimeError(f"expected transcript phrase missing: {phrase!r}; transcript={transcript!r}")
    if info.language != "en":
        raise RuntimeError(f"unexpected detected language: {info.language}")

    archive = dist_dir / "model.tar.gz"
    deterministic_tar_gz(model_dir, archive)
    fw_version = importlib.metadata.version("faster-whisper")
    ct2_version = importlib.metadata.version("ctranslate2")

    bundle_manifest = {
        "schema_version": 1,
        "logical_id": LOGICAL_ID,
        "upstream": {"provider": "huggingface", "repository": HF_REPO, "exact_revision": REVISION},
        "license": {
            "observed_spdx_id": "MIT",
            "redistribution_verified": True,
            "evidence": [
                f"https://huggingface.co/{HF_REPO}/tree/{REVISION}",
                f"https://huggingface.co/api/models/{HF_REPO}",
            ],
        },
        "format": {"family": "asr/faster-whisper", "format": "ctranslate2"},
        "files": [{k: entry[k] for k in ("path", "size_bytes", "sha256")} for entry in files],
        "archive": {
            "path": "model.tar.gz",
            "size_bytes": archive.stat().st_size,
            "sha256": sha256_file(archive),
        },
        "validation": {
            "profile": "faster-whisper-jfk-v1",
            "status": "passed",
            "faster_whisper_version": fw_version,
            "ctranslate2_version": ct2_version,
            "fixture": {
                "repository": "openai/whisper",
                "commit_sha": FIXTURE_COMMIT,
                "path": "tests/jfk.flac",
                "sha256": fixture_sha,
            },
            "claims": [
                "expected CTranslate2 files acquired from the exact upstream revision",
                "model loads from an explicit local directory with local_files_only enabled",
                "pinned JFK fixture transcribes in English with expected phrase checks",
            ],
            "transcript": transcript,
        },
        "source_metadata": source_meta,
    }
    (dist_dir / "bundle-manifest.json").write_text(
        json.dumps(bundle_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (dist_dir / "NOTICE.txt").write_text(
        "Model Artifact Foundry proof-of-concept bundle\n"
        f"Logical artifact: {LOGICAL_ID}\n"
        f"Source: https://huggingface.co/{HF_REPO}\n"
        f"Exact revision: {REVISION}\n"
        "Observed source license metadata: MIT\n"
        "Upstream model card describes this as a CTranslate2 conversion of OpenAI Whisper tiny.\n",
        encoding="utf-8",
    )
    shutil.rmtree(work)
    print(json.dumps({"logical_id": LOGICAL_ID, "archive_sha256": bundle_manifest["archive"]["sha256"],
                      "validation": bundle_manifest["validation"]["status"]}))


def verify_pulled(bundle_dir: Path) -> None:
    required = {"model.tar.gz", "bundle-manifest.json", "NOTICE.txt"}
    actual = {p.name for p in bundle_dir.iterdir() if p.is_file()}
    if actual != required:
        raise RuntimeError(f"pulled OCI layer set mismatch: {sorted(actual)}")
    manifest = json.loads((bundle_dir / "bundle-manifest.json").read_text(encoding="utf-8"))
    archive = bundle_dir / "model.tar.gz"
    if sha256_file(archive) != manifest["archive"]["sha256"]:
        raise RuntimeError("pulled archive hash mismatch")
    with tempfile.TemporaryDirectory(prefix="foundry-verify-") as td:
        model_dir = Path(td) / "model"
        model_dir.mkdir()
        safe_extract(archive, model_dir)
        verify_model_files(model_dir, manifest)
    print(json.dumps({"verified": True, "logical_id": manifest["logical_id"],
                      "archive_sha256": manifest["archive"]["sha256"]}))


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
                "component": "faster-whisper",
                "constraint": f"validated == {bundle['validation']['faster_whisper_version']}",
                "evidence": "faster-whisper-jfk-v1",
            },
            {
                "component": "ctranslate2",
                "constraint": f"validated == {bundle['validation']['ctranslate2_version']}",
                "evidence": "faster-whisper-jfk-v1",
            },
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
