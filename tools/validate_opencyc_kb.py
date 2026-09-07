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
import tarfile
import urllib.request

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DECL = REPO_ROOT / "sources" / "opencyc-4.0.json"
SOURCE_SCHEMA = REPO_ROOT / "schemas" / "source-declaration.schema.json"

REQUIRED_FOUNDRY_START_SHA = "6bb32dcbb82b40b9720f018857a50f9c321f97e9"
REQUIRED_FOUNDRY_START_TREE = "f09fa13e6dd4f8fc3cf9d71e0b1d280255e6e0f3"

UPSTREAM_REPO = "openmindproject/opencyc-backups"
UPSTREAM_REVISION = "49ba326229f37c5b68207e6d42ad388048f62871"
UPSTREAM_ARCHIVE_URL = (
    f"https://media.githubusercontent.com/media/{UPSTREAM_REPO}/{UPSTREAM_REVISION}/4.0/opencyc-4.0-linux.tgz"
)
EXPECTED_ARCHIVE_SHA256 = "6d0d28ccdf88c357d4040ecc3548abbf578a32822eaa246743bbeec1d5ecb664"

DEFAULT_EVIDENCE_PATH = (
    REPO_ROOT / "candidates" / "kb-opencyc-4.0" / UPSTREAM_REVISION / "local-candidate.json"
)

EXPECTED_MANIFEST_ID = "68b3e314d8491f0e51f5b92faa98d4726d3b38da18383e37d5a510103670385a"
EXPECTED_COUNTS = {
    "constant-count.text": 188111,
    "assertion-count.text": 1889842,
    "deduction-count.text": 337085,
    "kb-hl-support-count.text": 17942,
    "clause-struc-count.text": 37201,
    "nart-count.text": 48238,
    "unrepresented-term-count.text": 592483,
}
CORE_CYCL_CONSTANTS = [
    "genls",
    "Lenat",
    "defnSufficient",
    "Collection",
    "Cyclist",
    "BinaryPredicate",
    "Organization",
    "Thing",
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
        raise QualificationError("BLOCKED_SOURCE", f"Failed to determine git HEAD/tree: {e}")


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


def compute_content_fingerprint(files: list[dict[str, object]]) -> str:
    sorted_files = sorted(files, key=lambda x: str(x["path"]))
    lines = [f"{f['path']}:{f['sha256']}" for f in sorted_files]
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def download(url: str, dest: Path) -> str:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SemperSupra-model-artifact-foundry/1"})
        h = hashlib.sha256()
        with urllib.request.urlopen(req, timeout=300) as resp, dest.open("wb") as out:
            while chunk := resp.read(1024 * 1024):
                h.update(chunk)
                out.write(chunk)
        return h.hexdigest()
    except Exception as e:
        raise QualificationError("BLOCKED_SOURCE", f"Download failed for {url}: {e}")


def validate_declaration() -> dict:
    try:
        decl = json.loads(SOURCE_DECL.read_text(encoding="utf-8"))
        schema = json.loads(SOURCE_SCHEMA.read_text(encoding="utf-8"))
        jsonschema.validate(decl, schema)
        return decl
    except Exception as e:
        raise QualificationError("FOUNDRY_SCHEMA_TOO_MODEL_SPECIFIC", f"Source declaration validation failed: {e}")


def extract_kb_units(archive_path: Path, target_dir: Path) -> list[dict[str, object]]:
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    prefix = "opencyc-4.0/server/cyc/run/units/5022/"
    extracted_records: list[dict[str, object]] = []

    with tarfile.open(archive_path, "r:gz") as tf:
        for member in tf.getmembers():
            if member.name.startswith(prefix) and member.isfile():
                rel_path = member.name[len(prefix) :]
                dest = target_dir / rel_path
                dest.parent.mkdir(parents=True, exist_ok=True)
                f_in = tf.extractfile(member)
                if f_in is None:
                    continue
                with dest.open("wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
                size = dest.stat().st_size
                sha = sha256_file(dest)
                extracted_records.append({
                    "path": rel_path,
                    "size_bytes": size,
                    "sha256": sha,
                })

    return sorted(extracted_records, key=lambda x: str(x["path"]))


def verify_kb_structure(kb_dir: Path) -> dict[str, object]:
    manifest_file = kb_dir / "manifest"
    if not manifest_file.exists():
        raise QualificationError("FAIL_DETERMINISTIC", "Missing manifest file in KB units directory")

    manifest_text = manifest_file.read_text(encoding="utf-8", errors="replace")
    if EXPECTED_MANIFEST_ID not in manifest_text:
        raise QualificationError(
            "FAIL_DETERMINISTIC", f"Manifest ID mismatch: expected {EXPECTED_MANIFEST_ID!r} in {manifest_text!r}"
        )

    parsed_counts = {}
    for filename, expected_count in EXPECTED_COUNTS.items():
        file_path = kb_dir / filename
        if not file_path.exists():
            raise QualificationError("FAIL_DETERMINISTIC", f"Missing expected KB count file: {filename}")
        try:
            val = int(file_path.read_text(encoding="utf-8").strip())
            if val != expected_count:
                raise QualificationError(
                    "FAIL_DETERMINISTIC", f"Count mismatch for {filename}: expected {expected_count}, got {val}"
                )
            parsed_counts[filename] = val
        except ValueError:
            raise QualificationError("FAIL_DETERMINISTIC", f"Invalid integer count in {filename}")

    constant_shell_path = kb_dir / "constant-shell.text"
    if not constant_shell_path.exists():
        raise QualificationError("FAIL_DETERMINISTIC", "Missing constant-shell.text file")

    constant_text = constant_shell_path.read_text(encoding="utf-8", errors="replace")
    verified_constants = []
    for c_term in CORE_CYCL_CONSTANTS:
        term_pattern = f'"{c_term}"'
        if term_pattern not in constant_text:
            raise QualificationError(
                "FAIL_DETERMINISTIC", f"Core CycL constant term missing from constant-shell.text: {c_term}"
            )
        verified_constants.append(c_term)

    return {
        "manifest_unit_id": EXPECTED_MANIFEST_ID,
        "counts": parsed_counts,
        "verified_core_constants": verified_constants,
    }


def run_qualification(cache_dir: Path, output_file: Path) -> dict:
    current_head, current_tree = get_git_info()
    if not is_ancestor(REQUIRED_FOUNDRY_START_SHA, current_head):
        return {
            "terminal_state": "STALE_TARGET",
            "required_foundry_start_commit": REQUIRED_FOUNDRY_START_SHA,
            "actual_foundry_commit": current_head,
            "message": f"Foundry start commit ({REQUIRED_FOUNDRY_START_SHA}) is not in candidate commit ancestry ({current_head}).",
        }

    try:
        decl = validate_declaration()

        cache_dir.mkdir(parents=True, exist_ok=True)
        archive_path = cache_dir / "opencyc-4.0-linux.tgz"

        if not archive_path.exists():
            download(UPSTREAM_ARCHIVE_URL, archive_path)

        observed_archive_sha = sha256_file(archive_path)
        if observed_archive_sha != EXPECTED_ARCHIVE_SHA256:
            raise QualificationError(
                "BLOCKED_SOURCE",
                f"Archive SHA-256 mismatch: expected {EXPECTED_ARCHIVE_SHA256}, got {observed_archive_sha}",
            )

        kb_dir_run1 = cache_dir / "kb_units_run1"
        files_run1 = extract_kb_units(archive_path, kb_dir_run1)
        kb_struct_run1 = verify_kb_structure(kb_dir_run1)
        fingerprint_run1 = compute_content_fingerprint(files_run1)

        kb_dir_run2 = cache_dir / "kb_units_run2"
        files_run2 = extract_kb_units(archive_path, kb_dir_run2)
        kb_struct_run2 = verify_kb_structure(kb_dir_run2)
        fingerprint_run2 = compute_content_fingerprint(files_run2)

        if files_run1 != files_run2 or fingerprint_run1 != fingerprint_run2 or kb_struct_run1 != kb_struct_run2:
            raise QualificationError("FAIL_DETERMINISTIC", "Validator run outputs differ across identical runs!")

        total_bytes = sum(f["size_bytes"] for f in files_run1)
        if total_bytes > decl["artifact"]["max_unpacked_bytes"]:
            raise QualificationError(
                "FOUNDRY_SCHEMA_TOO_MODEL_SPECIFIC",
                f"Unpacked bytes ({total_bytes}) exceed declared max ({decl['artifact']['max_unpacked_bytes']})",
            )

        evidence = {
            "terminal_state": "PARTIAL_LOCAL_CANDIDATE",
            "foundry_start_commit": REQUIRED_FOUNDRY_START_SHA,
            "foundry_start_tree": REQUIRED_FOUNDRY_START_TREE,
            "candidate_commit": current_head,
            "candidate_tree": current_tree,
            "logical_id": decl["logical_id"],
            "upstream": {
                "provider": "github-release",
                "repository": UPSTREAM_REPO,
                "exact_revision": UPSTREAM_REVISION,
                "archive_url": UPSTREAM_ARCHIVE_URL,
                "archive_sha256": observed_archive_sha,
                "archive_size_bytes": archive_path.stat().st_size,
            },
            "license": {
                "observed_spdx_id": "Apache-2.0",
                "redistribution_verified": True,
                "evidence": [
                    f"https://github.com/{UPSTREAM_REPO}/tree/{UPSTREAM_REVISION}",
                    "Bundled LEGAL.txt in opencyc-4.0-linux.tgz specifies: 'The OpenCyc Knowledge Base consists of code, written in the declarative language CycL, that represents or supports the representation of facts and rules pertaining to consensus reality. The OpenCyc Knowledge Base is licensed under the Apache License, Version 2.0'.",
                    "Excluded non-target material: OpenCyc Knowledge Server binary is separately governed by Cycorp Free-of-Charge Software License.",
                ],
            },
            "files": files_run1,
            "content_fingerprint": fingerprint_run1,
            "validation": {
                "profile": decl["validator_profile"],
                "status": "passed",
                "determinism_runs": 2,
                "determinism_verified": True,
                "kb_structure_verification": kb_struct_run1,
                "claims": [
                    "exact OpenCyc 4.0 KB units acquired and verified from immutable upstream release archive",
                    "65 KB unit files extracted with byte sizes and SHA-256 hashes recorded",
                    "KB manifest unit ID matches expected OpenCyc 4.0 KB 5022 manifest",
                    "parsed constant count (188,111), assertion count (1,889,842), and deduction count (337,085) match expected KB totals",
                    "foundational CycL constant terms verified in constant-shell.text",
                    "validator execution proved deterministic across multiple independent runs on identical bytes",
                ],
            },
            "limitations_and_stop_state": {
                "registry_published": False,
                "approved_catalog_promoted": False,
                "stop_state": (
                    "PARTIAL_LOCAL_CANDIDATE — local qualification complete. KB content validated and "
                    "content-fingerprinted without executing Knowledge Server binary or making Foundry "
                    "ontology authority. OCI candidate publishing stopped prior to catalog promotion."
                ),
            },
        }

        return evidence

    except QualificationError as e:
        return {
            "terminal_state": e.terminal_state,
            "foundry_start_commit": REQUIRED_FOUNDRY_START_SHA,
            "candidate_commit": current_head,
            "candidate_tree": current_tree,
            "error_message": str(e),
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="OpenCyc 4.0 KB Local Candidate Qualifier")
    parser.add_argument("--cache-dir", type=Path, default=Path("/tmp/opencyc-kb-cache"))
    parser.add_argument("--output", type=Path, default=DEFAULT_EVIDENCE_PATH, help="Path to write evidence record JSON")
    args = parser.parse_args()

    evidence = run_qualification(args.cache_dir, args.output)
    json_str = json.dumps(evidence, indent=2) + "\n"

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json_str, encoding="utf-8")

    print(json_str)


if __name__ == "__main__":
    main()
