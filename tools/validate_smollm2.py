#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import urllib.request

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DECL = REPO_ROOT / "sources" / "smollm2-135m-instruct.json"
SOURCE_SCHEMA = REPO_ROOT / "schemas" / "source-declaration.schema.json"
LOGICAL_ID = "llm/smollm2/135m-instruct"
HF_REPO = "HuggingFaceTB/SmolLM2-135M-Instruct"
HF_API = f"https://huggingface.co/api/models/{HF_REPO}"
REVISION = "12fd25f77366fa6b3b4b768ec3050bf629380bac"
EXPECTED_FILES = (
    "config.json",
    "generation_config.json",
    "merges.txt",
    "model.safetensors",
    "special_tokens_map.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "vocab.json",
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "SemperSupra-model-artifact-foundry/1"})
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.load(response)


def download(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "SemperSupra-model-artifact-foundry/1"})
    with urllib.request.urlopen(req, timeout=600) as response, dest.open("wb") as output:
        shutil.copyfileobj(response, output)


def declaration() -> dict:
    data = json.loads(SOURCE_DECL.read_text(encoding="utf-8"))
    schema = json.loads(SOURCE_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(data, schema)
    if data["logical_id"] != LOGICAL_ID:
        raise RuntimeError("logical_id mismatch")
    if data["source"]["repository"] != HF_REPO or data["source"]["discovery_ref"] != REVISION:
        raise RuntimeError("source declaration repository/revision mismatch")
    if tuple(data["artifact"]["expected_file_patterns"]) != EXPECTED_FILES:
        raise RuntimeError("source declaration file allowlist mismatch")
    return data


def upstream_metadata(meta: dict) -> dict:
    if meta.get("id") != HF_REPO:
        raise RuntimeError(f"unexpected upstream id: {meta.get('id')!r}")
    if meta.get("sha") != REVISION:
        raise RuntimeError(
            f"upstream main moved: expected {REVISION}, observed {meta.get('sha')}; do not silently substitute"
        )
    if meta.get("private") or meta.get("disabled") or meta.get("gated") not in (False, None):
        raise RuntimeError("upstream access posture no longer matches public, enabled, non-gated contract")
    license_id = str((meta.get("cardData") or {}).get("license") or "").upper()
    if license_id != "APACHE-2.0":
        raise RuntimeError(f"expected Apache-2.0, observed {license_id!r}")
    siblings = {entry.get("rfilename") for entry in meta.get("siblings", [])}
    missing = sorted(set(EXPECTED_FILES) - siblings)
    if missing:
        raise RuntimeError(f"upstream missing expected inference files: {missing}")
    return {
        "id": meta["id"],
        "sha": meta["sha"],
        "license": license_id,
        "private": bool(meta.get("private")),
        "gated": meta.get("gated"),
        "disabled": bool(meta.get("disabled")),
    }


def content_manifest_material(files: list[dict]) -> dict:
    return {
        "schema_version": 1,
        "logical_id": LOGICAL_ID,
        "upstream": {
            "provider": "huggingface",
            "repository": HF_REPO,
            "exact_revision": REVISION,
        },
        "files": files,
    }


def content_manifest_digest(material: dict) -> str:
    canonical = json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(canonical).hexdigest()


def smoke(model_dir: Path) -> dict:
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    import torch
    import transformers
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(
        str(model_dir), local_files_only=True, trust_remote_code=False
    )
    model = AutoModelForCausalLM.from_pretrained(
        str(model_dir), local_files_only=True, trust_remote_code=False
    )
    model.eval()
    messages = [{"role": "user", "content": "Return only the digits for 17 + 25."}]
    rendered = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(rendered, return_tensors="pt")
    with torch.no_grad():
        outputs = model(**inputs, use_cache=False)
        finite = bool(torch.isfinite(outputs.logits).all().item())
        generated = model.generate(**inputs, do_sample=False, max_new_tokens=8)
    if not finite:
        raise RuntimeError("non-finite logits in local smoke")
    new_tokens = generated[0, inputs["input_ids"].shape[-1]:]
    text = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
    if not text:
        raise RuntimeError("empty deterministic generation in local smoke")
    return {
        "torch": torch.__version__,
        "transformers": transformers.__version__,
        "trust_remote_code": False,
        "local_files_only": True,
        "logits_finite": finite,
        "generated_text": text,
    }


def qualify(cache_dir: Path) -> tuple[dict, Path]:
    decl = declaration()
    meta = upstream_metadata(fetch_json(HF_API))
    model_dir = cache_dir / "model"
    model_dir.mkdir(parents=True, exist_ok=True)

    files: list[dict] = []
    total = 0
    for name in EXPECTED_FILES:
        dest = model_dir / name
        if not dest.exists():
            download(f"https://huggingface.co/{HF_REPO}/resolve/{REVISION}/{name}?download=true", dest)
        size = dest.stat().st_size
        total += size
        files.append({"path": name, "size_bytes": size, "sha256": sha256_file(dest)})
    files.sort(key=lambda item: item["path"])
    if total > decl["artifact"]["max_unpacked_bytes"]:
        raise RuntimeError(f"downloaded inference file set exceeds declared max bytes: {total}")

    material = content_manifest_material(files)
    digest = content_manifest_digest(material)
    smoke_result = smoke(model_dir)
    record = {
        "schema_version": 1,
        "logical_id": LOGICAL_ID,
        "state": "candidate",
        "artifact_identity": {"kind": "content-manifest", "digest": digest},
        "upstream": material["upstream"],
        "license": {
            "observed_spdx_id": "Apache-2.0",
            "redistribution_verified_for_declared_files": True,
            "evidence": [
                f"https://huggingface.co/{HF_REPO}/tree/{REVISION}",
                HF_API,
            ],
        },
        "files": files,
        "validation": {
            "profile": "smollm2-causal-lm-local-smoke-v1",
            "status": "passed",
            "claims": [
                "exact declared upstream revision reacquired",
                "only the declared non-pickle inference file allowlist was acquired",
                "content-manifest identity is deterministic over exact revision and sorted file hashes",
                "tokenizer and causal LM load offline with trust_remote_code disabled",
                "bounded deterministic CPU generation produced finite logits and non-empty output",
            ],
            "smoke": smoke_result,
        },
        "source_metadata": meta,
        "consumer": {
            "authority": "SemperSupra/model-spelunker#4",
            "purpose": "Model Spelunker shared-probe MVP",
        },
        "promotion": {
            "approved_catalog_modified": False,
            "oci_published": False,
        },
    }
    return record, model_dir


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache-dir", type=Path, default=Path("/tmp/foundry-smollm2"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    record, model_dir = qualify(args.cache_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "terminal_state": "PASS_CONTENT_MANIFEST_CANDIDATE",
        "logical_id": record["logical_id"],
        "artifact_identity": record["artifact_identity"],
        "model_dir": str(model_dir),
        "python": sys.version.split()[0],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
