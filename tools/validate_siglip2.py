#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DECL = REPO_ROOT / "sources" / "siglip2-base-patch16-224.json"
SOURCE_SCHEMA = REPO_ROOT / "schemas" / "source-declaration.schema.json"

REQUIRED_FOUNDRY_BASE_SHA = "22c661e138c5ec75bce0df8fa8fb62173bc3d02d"
ANALYZER_PR_TARGET = "mark-e-deyoung/content-analyzers-private PR #1"
ANALYZER_HEAD_SHA = "7c050b7ddbf37217c13d1e4f9fdaffdbc5a683b2"

HF_REPO = "google/siglip2-base-patch16-224"
HF_API = f"https://huggingface.co/api/models/{HF_REPO}"
REVISION = "75de2d55ec2d0b4efc50b3e9ad70dba96a7b2fa2"
DEFAULT_EVIDENCE_PATH = REPO_ROOT / "candidates" / "embed-siglip2-base-patch16-224" / REVISION / "local-candidate.json"

EXPECTED_FILES = [
    "config.json",
    "model.safetensors",
    "preprocessor_config.json",
    "special_tokens_map.json",
    "tokenizer.json",
    "tokenizer.model",
    "tokenizer_config.json",
]


class QualificationError(Exception):
    def __init__(self, terminal_state: str, message: str):
        super().__init__(message)
        self.terminal_state = terminal_state


def get_git_info() -> tuple[str, str]:
    try:
        head_res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        tree_res = subprocess.run(
            ["git", "rev-parse", "HEAD^{tree}"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        return head_res.stdout.strip(), tree_res.stdout.strip()
    except Exception as e:
        raise QualificationError("BLOCKED_ENVIRONMENT", f"Failed to determine git HEAD/tree: {e}")


def is_ancestor(ancestor_sha: str, descendant_sha: str = "HEAD") -> bool:
    if ancestor_sha == descendant_sha:
        return True
    try:
        res = subprocess.run(
            ["git", "merge-base", "--is-ancestor", ancestor_sha, descendant_sha],
            cwd=REPO_ROOT,
            capture_output=True,
            check=False,
        )
        if res.returncode == 0:
            return True
        shallow_check = subprocess.run(
            ["git", "rev-parse", "--is-shallow-repository"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if shallow_check.stdout.strip() == "true":
            subprocess.run(["git", "fetch", "--unshallow"], cwd=REPO_ROOT, capture_output=True, check=False)
            res2 = subprocess.run(
                ["git", "merge-base", "--is-ancestor", ancestor_sha, descendant_sha],
                cwd=REPO_ROOT,
                capture_output=True,
                check=False,
            )
            return res2.returncode == 0
        return False
    except Exception:
        return False


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_json(url: str) -> dict:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SemperSupra-model-artifact-foundry/1"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.load(resp)
    except Exception as e:
        raise QualificationError("BLOCKED_ENVIRONMENT", f"Network or API failure fetching {url}: {e}")


def download(url: str, dest: Path) -> None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SemperSupra-model-artifact-foundry/1"})
        with urllib.request.urlopen(req, timeout=300) as resp, dest.open("wb") as out:
            shutil.copyfileobj(resp, out)
    except Exception as e:
        raise QualificationError("BLOCKED_ENVIRONMENT", f"Download failed for {url}: {e}")


def validate_declaration() -> dict:
    try:
        decl = json.loads(SOURCE_DECL.read_text(encoding="utf-8"))
        schema = json.loads(SOURCE_SCHEMA.read_text(encoding="utf-8"))
        jsonschema.validate(decl, schema)
        return decl
    except Exception as e:
        raise QualificationError("BLOCKED_CONTRACT", f"Source declaration schema validation failed: {e}")


def validate_upstream_metadata(meta: dict) -> dict:
    if meta.get("id") != HF_REPO:
        raise QualificationError("BLOCKED_CONTRACT", f"Unexpected upstream id: {meta.get('id')!r}")
    if meta.get("sha") != REVISION:
        raise QualificationError("BLOCKED_CONTRACT", f"Upstream commit mismatch: expected {REVISION}, observed {meta.get('sha')}")
    if meta.get("private"):
        raise QualificationError("BLOCKED_LICENSE", "Upstream repository is private")
    if meta.get("gated") not in (False, None):
        raise QualificationError("BLOCKED_LICENSE", f"Upstream repository is gated: {meta.get('gated')!r}")
    if meta.get("disabled"):
        raise QualificationError("BLOCKED_LICENSE", "Upstream repository is disabled")

    card = meta.get("cardData") or {}
    license_id = str(card.get("license") or "").upper()
    if license_id != "APACHE-2.0":
        raise QualificationError("BLOCKED_LICENSE", f"Expected Apache-2.0 license, observed {license_id!r}")

    siblings = {x.get("rfilename") for x in meta.get("siblings", [])}
    missing = set(EXPECTED_FILES) - siblings
    if missing:
        raise QualificationError("BLOCKED_CONTRACT", f"Upstream missing expected files: {sorted(missing)}")

    return {
        "id": meta["id"],
        "sha": meta["sha"],
        "license": license_id,
        "private": bool(meta.get("private")),
        "gated": meta.get("gated"),
        "disabled": bool(meta.get("disabled")),
        "siblings": sorted(x for x in siblings if x),
    }


def run_local_qualification(cache_dir: Path, command_str: str = "python3 tools/validate_siglip2.py") -> dict:
    current_head, current_tree = get_git_info()
    if not is_ancestor(REQUIRED_FOUNDRY_BASE_SHA, current_head):
        return {
            "terminal_state": "STALE_TARGET",
            "required_foundry_base_commit": REQUIRED_FOUNDRY_BASE_SHA,
            "actual_foundry_base_commit": current_head,
            "message": f"Foundry base commit ({REQUIRED_FOUNDRY_BASE_SHA}) is not in candidate commit ancestry ({current_head}).",
        }

    try:
        decl = validate_declaration()
        meta = validate_upstream_metadata(fetch_json(HF_API))

        model_dir = cache_dir / HF_REPO / REVISION
        model_dir.mkdir(parents=True, exist_ok=True)

        file_records = []
        for fname in EXPECTED_FILES:
            dest = model_dir / fname
            if not dest.exists():
                url = f"https://huggingface.co/{HF_REPO}/resolve/{REVISION}/{fname}?download=true"
                download(url, dest)
            size = dest.stat().st_size
            sha = sha256_file(dest)
            file_records.append({
                "path": fname,
                "size_bytes": size,
                "sha256": sha,
            })

        total_bytes = sum(f["size_bytes"] for f in file_records)
        if total_bytes > decl["artifact"]["max_unpacked_bytes"]:
            raise QualificationError("BLOCKED_CONTRACT", f"Unpacked bytes ({total_bytes}) exceed declared max ({decl['artifact']['max_unpacked_bytes']})")

        # Offline local smoke test
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"

        try:
            import PIL.Image
            import torch
            import transformers
            from transformers import AutoModel, AutoProcessor
        except ImportError as e:
            raise QualificationError("BLOCKED_ENVIRONMENT", f"Missing required ML framework libraries: {e}")

        try:
            model = AutoModel.from_pretrained(str(model_dir), local_files_only=True, trust_remote_code=False)
            processor = AutoProcessor.from_pretrained(str(model_dir), local_files_only=True, trust_remote_code=False)

            img = PIL.Image.new("RGB", (100, 100), color=(128, 64, 200))
            texts = ["a photo of a cat", "a photo of a dog", "synthetic test image"]

            inputs = processor(text=texts, images=img, return_tensors="pt", padding=True)

            with torch.no_grad():
                outputs = model(**inputs)
                image_embeds = outputs.image_embeds if hasattr(outputs, "image_embeds") else model.get_image_features(inputs["pixel_values"])
                text_embeds = outputs.text_embeds if hasattr(outputs, "text_embeds") else model.get_text_features(inputs["input_ids"])

            img_shape = list(image_embeds.shape)
            txt_shape = list(text_embeds.shape)
            img_finite = bool(torch.isfinite(image_embeds).all().item())
            txt_finite = bool(torch.isfinite(text_embeds).all().item())

            if not img_finite or not txt_finite:
                raise QualificationError("FAIL_DETERMINISTIC", "Embeddings contain non-finite values (NaN or Inf)")

            if img_shape != [1, 768]:
                raise QualificationError("FAIL_DETERMINISTIC", f"Unexpected image embeddings shape: {img_shape}")

            if txt_shape != [3, 768]:
                raise QualificationError("FAIL_DETERMINISTIC", f"Unexpected text embeddings shape: {txt_shape}")

        except QualificationError:
            raise
        except Exception as e:
            raise QualificationError("FAIL_DETERMINISTIC", f"Local model smoke test failed: {e}")

        evidence = {
            "terminal_state": "PASS_LOCAL_CANDIDATE",
            "foundry_base_commit": REQUIRED_FOUNDRY_BASE_SHA,
            "candidate_commit": current_head,
            "candidate_tree": current_tree,
            "logical_id": decl["logical_id"],
            "upstream": {
                "provider": "huggingface",
                "repository": HF_REPO,
                "exact_revision": REVISION,
                "observed_license_spdx": meta["license"],
                "redistribution_verified": True,
                "evidence_urls": [
                    f"https://huggingface.co/{HF_REPO}/tree/{REVISION}",
                    HF_API,
                ],
            },
            "consumer_context": {
                "target": ANALYZER_PR_TARGET,
                "analyzer_head": ANALYZER_HEAD_SHA,
            },
            "framework_versions": {
                "python": sys.version.split()[0],
                "torch": torch.__version__,
                "transformers": transformers.__version__,
                "pillow": PIL.__version__,
            },
            "files": file_records,
            "local_smoke_results": {
                "command": command_str,
                "image_embeddings_shape": img_shape,
                "text_embeddings_shape": txt_shape,
                "image_embeddings_finite": img_finite,
                "text_embeddings_finite": txt_finite,
                "trust_remote_code": False,
                "local_files_only": True,
            },
            "limitations_and_stop_state": {
                "registry_published": False,
                "approved_catalog_promoted": False,
                "analyzer_semantics_changed": False,
                "stop_state": "PASS_LOCAL_CANDIDATE — local qualification complete. Model artifact downloads restricted to ephemeral VM cache. Next packaging, OCI publishing, catalog promotion, and live analyzer qualification steps remain separately unblocked.",
            },
        }
        return evidence
    except QualificationError as e:
        return {
            "terminal_state": e.terminal_state,
            "foundry_base_commit": REQUIRED_FOUNDRY_BASE_SHA,
            "candidate_commit": current_head,
            "candidate_tree": current_tree,
            "error_message": str(e),
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="SigLIP2 Local Candidate Qualifier")
    parser.add_argument("--cache-dir", type=Path, default=Path("/tmp/siglip2-cache"))
    parser.add_argument("--output", type=Path, default=DEFAULT_EVIDENCE_PATH, help="Path to write evidence record JSON")
    args = parser.parse_args()

    command_str = " ".join([sys.executable] + sys.argv)
    evidence = run_local_qualification(args.cache_dir, command_str=command_str)
    json_str = json.dumps(evidence, indent=2) + "\n"

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json_str, encoding="utf-8")

    print(json_str)


if __name__ == "__main__":
    main()
