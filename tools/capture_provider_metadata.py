#!/usr/bin/env python3
"""Capture metadata-only provider evidence for Foundry issue #12.

The capture path is intentionally read-only and unauthenticated. It never downloads
model/checkpoint bytes and never accepts provider credentials. Output is JSON only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

USER_AGENT = "SemperSupra-model-artifact-foundry/issue-12-metadata-capture"
SENSITIVE_KEYS = {
    "authorization",
    "cookie",
    "set-cookie",
    "set_cookie",
    "api-key",
    "api_key",
    "apikey",
    "access-token",
    "access_token",
    "refresh-token",
    "refresh_token",
    "password",
    "secret",
    "token",
    "hf_token",
}
SENSITIVE_VALUE_PATTERNS = (
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+\-/]+=*"),
    re.compile(r"\bhf_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def fetch_json(url: str) -> Any:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            content_type = response.headers.get_content_type()
            if content_type not in {"application/json", "text/json"}:
                raise RuntimeError(f"unexpected content type {content_type!r} from {url}")
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code} while reading metadata from {url}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"unable to read metadata from {url}: {exc.reason}") from exc


def sensitive_findings(value: Any, path: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = str(key).strip().lower()
            if normalized in SENSITIVE_KEYS:
                findings.append(f"{path}.{key}: sensitive key")
            findings.extend(sensitive_findings(item, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            findings.extend(sensitive_findings(item, f"{path}[{index}]"))
    elif isinstance(value, str):
        for pattern in SENSITIVE_VALUE_PATTERNS:
            if pattern.search(value):
                findings.append(f"{path}: sensitive-looking value")
                break
    return findings


def require_public_safe(value: Any) -> None:
    findings = sensitive_findings(value)
    if findings:
        joined = "\n  - ".join(findings)
        raise RuntimeError(f"refusing to write fixture with sensitive material:\n  - {joined}")


def write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
    ) as handle:
        handle.write(payload)
        temp_name = handle.name
    os.replace(temp_name, path)


def hf_url(repo_id: str, revision: str) -> str:
    quoted_repo = "/".join(urllib.parse.quote(part, safe="") for part in repo_id.split("/"))
    if revision == "main":
        return f"https://huggingface.co/api/models/{quoted_repo}?blobs=true"
    quoted_revision = urllib.parse.quote(revision, safe="")
    return f"https://huggingface.co/api/models/{quoted_repo}/revision/{quoted_revision}?blobs=true"


def capture_huggingface(args: argparse.Namespace) -> tuple[Any, dict[str, Any]]:
    url = hf_url(args.repo, args.revision)
    value = fetch_json(url)
    provenance = {
        "provider": "huggingface",
        "endpoint_class": "model-info-with-file-metadata",
        "request": {"repo": args.repo, "revision": args.revision, "files_metadata": True},
        "source_url": url,
        "captured_at": utc_now(),
        "authentication": "none",
        "sanitization": "sensitive-key/value scan; no credential inputs accepted",
        "projection": "none",
    }
    return value, provenance


def capture_civitai(args: argparse.Namespace) -> tuple[Any, dict[str, Any]]:
    url = f"https://civitai.com/api/v1/model-versions/{args.version_id}"
    value = fetch_json(url)
    provenance = {
        "provider": "civitai",
        "endpoint_class": "model-version",
        "request": {"model_version_id": args.version_id},
        "source_url": url,
        "captured_at": utc_now(),
        "authentication": "none",
        "sanitization": "sensitive-key/value scan; no credential inputs accepted",
        "projection": "none",
    }
    return value, provenance


def capture_openrouter(args: argparse.Namespace) -> tuple[Any, dict[str, Any]]:
    url = "https://openrouter.ai/api/v1/models"
    value = fetch_json(url)
    projection = "none"
    if args.model_id:
        matches = [item for item in value.get("data", []) if item.get("id") == args.model_id]
        if len(matches) != 1:
            raise RuntimeError(
                f"expected exactly one OpenRouter model with id {args.model_id!r}; found {len(matches)}"
            )
        value = {"data": matches}
        projection = "selected model record from /api/v1/models"
    provenance = {
        "provider": "openrouter",
        "endpoint_class": "model-list",
        "request": {"model_id_filter": args.model_id},
        "source_url": url,
        "captured_at": utc_now(),
        "authentication": "none",
        "sanitization": "sensitive-key/value scan; no credential inputs accepted",
        "projection": projection,
        "identity_note": "hosted provider identity; do not infer a model artifact content digest",
    }
    return value, provenance


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--output", type=Path, required=True, help="fixture JSON output path")
    root.add_argument(
        "--provenance-output",
        type=Path,
        help="provenance sidecar path (default: <output>.provenance.json)",
    )
    providers = root.add_subparsers(dest="provider", required=True)

    hf = providers.add_parser("huggingface")
    hf.add_argument("--repo", required=True)
    hf.add_argument("--revision", default="main")
    hf.set_defaults(capture=capture_huggingface)

    civitai = providers.add_parser("civitai")
    civitai.add_argument("--version-id", required=True, type=int)
    civitai.set_defaults(capture=capture_civitai)

    openrouter = providers.add_parser("openrouter")
    openrouter.add_argument("--model-id")
    openrouter.set_defaults(capture=capture_openrouter)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        value, provenance = args.capture(args)
        require_public_safe(value)
        require_public_safe(provenance)
        provenance_path = args.provenance_output or args.output.with_suffix(
            args.output.suffix + ".provenance.json"
        )
        write_json_atomic(args.output, value)
        write_json_atomic(provenance_path, provenance)
    except (RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
