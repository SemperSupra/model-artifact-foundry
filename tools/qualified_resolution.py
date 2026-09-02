#!/usr/bin/env python3
"""Retain and resolve qualified first-consumer model decisions deterministically."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
from pathlib import Path
from types import ModuleType
from typing import Any

_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_TOOLS = Path(__file__).resolve().parent


class QualifiedResolutionError(ValueError):
    """Raised when a retained qualified-resolution binding is invalid or conflicting."""


def _load_tool(name: str, filename: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, _TOOLS / filename)
    if spec is None or spec.loader is None:
        raise QualifiedResolutionError(f"unable to load dependency tool {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


REQUEST = _load_tool("foundry_model_request_contract", "model_request_contract.py")
QUALIFICATION = _load_tool("foundry_qualification_receipt", "qualification_receipt.py")


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"


def sha256_json(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _object(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise QualifiedResolutionError(f"{context} must be an object")
    return value


def _keys(value: dict[str, Any], context: str, required: set[str]) -> None:
    missing = required - set(value)
    extra = set(value) - required
    if missing:
        raise QualifiedResolutionError(f"{context} missing fields: {', '.join(sorted(missing))}")
    if extra:
        raise QualifiedResolutionError(f"{context} has unexpected fields: {', '.join(sorted(extra))}")


def _text(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value:
        raise QualifiedResolutionError(f"{context} must be a non-empty string")
    return value


def _digest(value: Any, context: str) -> str:
    text = _text(value, context)
    if _DIGEST_RE.fullmatch(text) is None:
        raise QualifiedResolutionError(f"{context} must be sha256:<64 lowercase hex>")
    return text


def _normalize_runtime_context(
    runtime_doc: Any,
    *,
    context: str = "runtime",
    request: dict[str, Any] | None = None,
) -> dict[str, str]:
    runtime = _object(runtime_doc, context)
    _keys(runtime, context, {"id", "toolchain_digest", "config_digest"})
    normalized = {
        "id": _text(runtime["id"], f"{context}.id"),
        "toolchain_digest": _digest(runtime["toolchain_digest"], f"{context}.toolchain_digest"),
        "config_digest": _digest(runtime["config_digest"], f"{context}.config_digest"),
    }
    if request is not None and normalized["id"] not in request["runtime"]["allowed_ids"]:
        raise QualifiedResolutionError("runtime context is not allowed by request")
    return normalized


def resolution_context(
    request_doc: Any,
    environment_digest: str,
    runtime_doc: Any,
) -> dict[str, Any]:
    request = REQUEST.normalize_request(request_doc)
    return {
        "request_digest": REQUEST.request_digest(request),
        "target_profile_id": request["target"]["profile_id"],
        "environment_digest": _digest(environment_digest, "environment_digest"),
        "runtime": _normalize_runtime_context(runtime_doc, context="runtime", request=request),
    }


def resolution_key(context: Any) -> str:
    context = _object(context, "resolution")
    _keys(
        context,
        "resolution",
        {"request_digest", "target_profile_id", "environment_digest", "runtime"},
    )
    normalized = {
        "request_digest": _digest(context["request_digest"], "resolution.request_digest"),
        "target_profile_id": _text(context["target_profile_id"], "resolution.target_profile_id"),
        "environment_digest": _digest(context["environment_digest"], "resolution.environment_digest"),
        "runtime": _normalize_runtime_context(context["runtime"], context="resolution.runtime"),
    }
    return sha256_json(normalized)


def binding_filename(key: str) -> str:
    key = _digest(key, "resolution_key")
    return key.removeprefix("sha256:") + ".json"


def _selection_from_subject(subject: dict[str, Any]) -> dict[str, Any]:
    artifact = subject["artifact"]
    representation = subject["representation"]
    runtime = subject["runtime"]
    target = subject["target"]
    return {
        "artifact": {
            "provider": artifact["provider"],
            "repository": artifact["repository"],
            "source_revision": artifact["source_revision"],
            "observation_digest": artifact["observation_digest"],
        },
        "representation": {
            "id": representation["id"],
            "variant": representation["variant"],
            "quantization": representation["quantization"],
        },
        "runtime": {"id": runtime["id"]},
        "target_profile_id": target["profile_id"],
    }


def _with_binding_digest(body: dict[str, Any]) -> dict[str, Any]:
    return {**body, "binding_digest": sha256_json(body)}


def binding_from_qualified_receipt(
    request_doc: Any,
    environment_digest: str,
    runtime_doc: Any,
    receipt_doc: Any,
) -> dict[str, Any]:
    request = REQUEST.normalize_request(request_doc)
    request_digest = REQUEST.request_digest(request)
    runtime_context = _normalize_runtime_context(runtime_doc, context="runtime", request=request)
    try:
        receipt = QUALIFICATION.validate_receipt(receipt_doc)
    except Exception as exc:
        raise QualifiedResolutionError(f"qualification receipt is invalid: {exc}") from exc

    if receipt["result"]["outcome"] != "qualified":
        raise QualifiedResolutionError("only a qualified receipt may create a retained resolution")

    subject = receipt["subject"]
    if subject["request"]["digest"] != request_digest:
        raise QualifiedResolutionError("qualification request digest does not match canonical request")
    if subject["target"]["profile_id"] != request["target"]["profile_id"]:
        raise QualifiedResolutionError("qualification target profile does not match request")
    env_digest = _digest(environment_digest, "environment_digest")
    if subject["target"]["environment_digest"] != env_digest:
        raise QualifiedResolutionError("qualification environment digest does not match lookup environment")
    subject_runtime = _normalize_runtime_context(
        subject["runtime"], context="qualification.subject.runtime", request=request
    )
    if subject_runtime != runtime_context:
        raise QualifiedResolutionError("qualification runtime context does not match lookup runtime")

    selection = _selection_from_subject(subject)
    qualified_result = {
        "schema_version": 1,
        "request_digest": request_digest,
        "status": "qualified",
        "reasons": [],
        "evidence": [],
        "selection": selection,
        "qualification": {
            "subject_key": receipt["subject_key"],
            "record_digest": receipt["record_digest"],
        },
    }
    try:
        REQUEST.normalize_result(qualified_result, request)
    except Exception as exc:
        raise QualifiedResolutionError(f"qualified selection does not satisfy request: {exc}") from exc

    context = resolution_context(request, env_digest, runtime_context)
    body = {
        "schema_version": 1,
        "resolution": context,
        "resolution_key": resolution_key(context),
        "qualification": {
            "subject_key": receipt["subject_key"],
            "record_digest": receipt["record_digest"],
        },
        "selection": selection,
    }
    return _with_binding_digest(body)


def validate_binding(binding_doc: Any) -> dict[str, Any]:
    binding = _object(binding_doc, "binding")
    _keys(
        binding,
        "binding",
        {"schema_version", "resolution", "resolution_key", "qualification", "selection", "binding_digest"},
    )
    if binding["schema_version"] != 1:
        raise QualifiedResolutionError("binding.schema_version must be 1")

    context = _object(binding["resolution"], "binding.resolution")
    _keys(
        context,
        "binding.resolution",
        {"request_digest", "target_profile_id", "environment_digest", "runtime"},
    )
    context = {
        "request_digest": _digest(context["request_digest"], "binding.resolution.request_digest"),
        "target_profile_id": _text(context["target_profile_id"], "binding.resolution.target_profile_id"),
        "environment_digest": _digest(context["environment_digest"], "binding.resolution.environment_digest"),
        "runtime": _normalize_runtime_context(
            context["runtime"], context="binding.resolution.runtime"
        ),
    }
    expected_key = resolution_key(context)
    if _digest(binding["resolution_key"], "binding.resolution_key") != expected_key:
        raise QualifiedResolutionError("binding.resolution_key does not match canonical resolution context")

    qualification = _object(binding["qualification"], "binding.qualification")
    _keys(qualification, "binding.qualification", {"subject_key", "record_digest"})
    qualification = {
        "subject_key": _digest(qualification["subject_key"], "binding.qualification.subject_key"),
        "record_digest": _digest(qualification["record_digest"], "binding.qualification.record_digest"),
    }

    selection = _object(binding["selection"], "binding.selection")
    _keys(selection, "binding.selection", {"artifact", "representation", "runtime", "target_profile_id"})
    artifact = _object(selection["artifact"], "binding.selection.artifact")
    _keys(artifact, "binding.selection.artifact", {"provider", "repository", "source_revision", "observation_digest"})
    artifact = {
        "provider": _text(artifact["provider"], "binding.selection.artifact.provider"),
        "repository": _text(artifact["repository"], "binding.selection.artifact.repository"),
        "source_revision": _text(artifact["source_revision"], "binding.selection.artifact.source_revision"),
        "observation_digest": _digest(artifact["observation_digest"], "binding.selection.artifact.observation_digest"),
    }
    representation = _object(selection["representation"], "binding.selection.representation")
    _keys(representation, "binding.selection.representation", {"id", "variant", "quantization"})
    representation = {
        "id": _text(representation["id"], "binding.selection.representation.id"),
        "variant": _text(representation["variant"], "binding.selection.representation.variant"),
        "quantization": _text(representation["quantization"], "binding.selection.representation.quantization"),
    }
    runtime = _object(selection["runtime"], "binding.selection.runtime")
    _keys(runtime, "binding.selection.runtime", {"id"})
    runtime = {"id": _text(runtime["id"], "binding.selection.runtime.id")}
    target_profile_id = _text(selection["target_profile_id"], "binding.selection.target_profile_id")
    if target_profile_id != context["target_profile_id"]:
        raise QualifiedResolutionError("binding selection target does not match resolution target")
    if runtime["id"] != context["runtime"]["id"]:
        raise QualifiedResolutionError("binding selection runtime does not match resolution runtime")

    body = {
        "schema_version": 1,
        "resolution": context,
        "resolution_key": expected_key,
        "qualification": qualification,
        "selection": {
            "artifact": artifact,
            "representation": representation,
            "runtime": runtime,
            "target_profile_id": target_profile_id,
        },
    }
    expected_digest = sha256_json(body)
    if _digest(binding["binding_digest"], "binding.binding_digest") != expected_digest:
        raise QualifiedResolutionError("binding_digest does not match canonical binding body")
    normalized = {**body, "binding_digest": expected_digest}
    if normalized != binding:
        raise QualifiedResolutionError("binding is not in canonical normalized form")
    return binding


def retain_binding(store: str | Path, binding_doc: Any) -> Path:
    binding = validate_binding(binding_doc)
    directory = Path(store)
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / binding_filename(binding["resolution_key"])
    canonical = canonical_json(binding)

    if destination.exists():
        existing = json.loads(destination.read_text(encoding="utf-8"))
        validate_binding(existing)
        if canonical_json(existing) != canonical:
            raise QualifiedResolutionError("existing resolution key has conflicting retained content")
        return destination

    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(canonical, encoding="utf-8")
    temporary.replace(destination)
    return destination


def lookup(
    request_doc: Any,
    environment_digest: str,
    runtime_doc: Any,
    store: str | Path,
) -> dict[str, Any]:
    request = REQUEST.normalize_request(request_doc)
    context = resolution_context(request, environment_digest, runtime_doc)
    key = resolution_key(context)
    path = Path(store) / binding_filename(key)

    if not path.exists():
        return REQUEST.normalize_result(
            {
                "schema_version": 1,
                "request_digest": context["request_digest"],
                "status": "unknown",
                "reasons": ["no_retained_qualified_resolution"],
                "evidence": [],
            },
            request,
        )

    try:
        binding = validate_binding(json.loads(path.read_text(encoding="utf-8")))
    except Exception as exc:
        raise QualifiedResolutionError(f"retained resolution is malformed or tampered: {exc}") from exc
    if binding["resolution"] != context:
        raise QualifiedResolutionError("retained resolution context does not match lookup context")

    result = {
        "schema_version": 1,
        "request_digest": context["request_digest"],
        "status": "qualified",
        "reasons": [],
        "evidence": [
            {
                "kind": "retained_resolution_binding",
                "digest": binding["binding_digest"],
                "ref": f"resolution://{binding['resolution_key']}",
                "visibility": "local",
            }
        ],
        "selection": binding["selection"],
        "qualification": binding["qualification"],
    }
    return REQUEST.normalize_result(result, request)


def _load(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise QualifiedResolutionError(f"{path}: top-level value must be an object")
    return value


def _write(path: str | Path, value: dict[str, Any]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".tmp")
    temporary.write_text(canonical_json(value), encoding="utf-8")
    temporary.replace(destination)


def _runtime_from_args(args: argparse.Namespace) -> dict[str, str]:
    return {
        "id": args.runtime_id,
        "toolchain_digest": args.runtime_toolchain_digest,
        "config_digest": args.runtime_config_digest,
    }


def _add_runtime_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--runtime-id", required=True)
    parser.add_argument("--runtime-toolchain-digest", required=True)
    parser.add_argument("--runtime-config-digest", required=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    retain = subparsers.add_parser("retain")
    retain.add_argument("--request", required=True)
    retain.add_argument("--environment-digest", required=True)
    _add_runtime_args(retain)
    retain.add_argument("--receipt", required=True)
    retain.add_argument("--store", required=True)

    lookup_parser = subparsers.add_parser("lookup")
    lookup_parser.add_argument("--request", required=True)
    lookup_parser.add_argument("--environment-digest", required=True)
    _add_runtime_args(lookup_parser)
    lookup_parser.add_argument("--store", required=True)
    lookup_parser.add_argument("--output")

    args = parser.parse_args()
    request_doc = _load(args.request)
    runtime = _runtime_from_args(args)

    if args.command == "retain":
        binding = binding_from_qualified_receipt(
            request_doc,
            args.environment_digest,
            runtime,
            _load(args.receipt),
        )
        path = retain_binding(args.store, binding)
        print(path)
        return 0

    result = lookup(request_doc, args.environment_digest, runtime, args.store)
    if args.output:
        _write(args.output, result)
    else:
        print(canonical_json(result), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
