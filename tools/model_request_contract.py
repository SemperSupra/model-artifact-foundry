#!/usr/bin/env python3
"""Canonicalize first-consumer model requests and validate deterministic plan results."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class ModelRequestContractError(ValueError):
    """Raised when a request/result violates the v1 first-consumer contract."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"


def sha256_json(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _object(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ModelRequestContractError(f"{context} must be an object")
    return value


def _keys(
    value: dict[str, Any],
    context: str,
    required: set[str],
    optional: set[str] | None = None,
) -> None:
    optional = optional or set()
    actual = set(value)
    missing = required - actual
    extra = actual - required - optional
    if missing:
        raise ModelRequestContractError(f"{context} missing fields: {', '.join(sorted(missing))}")
    if extra:
        raise ModelRequestContractError(f"{context} has unexpected fields: {', '.join(sorted(extra))}")


def _text(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value:
        raise ModelRequestContractError(f"{context} must be a non-empty string")
    return value


def _digest(value: Any, context: str) -> str:
    value = _text(value, context)
    if _DIGEST_RE.fullmatch(value) is None:
        raise ModelRequestContractError(f"{context} must be sha256:<64 lowercase hex>")
    return value


def _sorted_unique_strings(value: Any, context: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ModelRequestContractError(f"{context} must be a non-empty array")
    if any(not isinstance(item, str) or not item for item in value):
        raise ModelRequestContractError(f"{context} entries must be non-empty strings")
    if len(set(value)) != len(value):
        raise ModelRequestContractError(f"{context} must not contain duplicates")
    return sorted(value)


def _positive_number(value: Any, context: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ModelRequestContractError(f"{context} must be a positive finite number")
    if not math.isfinite(float(value)) or value <= 0:
        raise ModelRequestContractError(f"{context} must be a positive finite number")
    return value


def normalize_request(request: Any) -> dict[str, Any]:
    request = _object(request, "request")
    _keys(
        request,
        "request",
        {"schema_version", "capability", "target", "runtime", "representation", "envelope", "quality_policy"},
    )
    if request["schema_version"] != 1:
        raise ModelRequestContractError("request.schema_version must be 1")

    capability = _object(request["capability"], "request.capability")
    _keys(capability, "request.capability", {"id", "interface"})
    capability_out = {
        "id": _text(capability["id"], "request.capability.id"),
        "interface": _text(capability["interface"], "request.capability.interface"),
    }

    target = _object(request["target"], "request.target")
    _keys(target, "request.target", {"profile_id"})
    target_out = {"profile_id": _text(target["profile_id"], "request.target.profile_id")}

    runtime = _object(request["runtime"], "request.runtime")
    _keys(runtime, "request.runtime", {"offline_required", "allowed_ids"})
    if not isinstance(runtime["offline_required"], bool):
        raise ModelRequestContractError("request.runtime.offline_required must be boolean")
    runtime_out = {
        "offline_required": runtime["offline_required"],
        "allowed_ids": _sorted_unique_strings(runtime["allowed_ids"], "request.runtime.allowed_ids"),
    }

    representation = _object(request["representation"], "request.representation")
    _keys(representation, "request.representation", {"allowed_ids", "allowed_quantizations"})
    representation_out = {
        "allowed_ids": _sorted_unique_strings(
            representation["allowed_ids"], "request.representation.allowed_ids"
        ),
        "allowed_quantizations": _sorted_unique_strings(
            representation["allowed_quantizations"], "request.representation.allowed_quantizations"
        ),
    }

    envelope = _object(request["envelope"], "request.envelope")
    allowed_envelope = {
        "max_peak_vram_gib",
        "max_model_load_seconds",
        "max_p95_query_latency_ms",
    }
    _keys(envelope, "request.envelope", set(), allowed_envelope)
    envelope_out = {
        key: _positive_number(envelope[key], f"request.envelope.{key}")
        for key in sorted(envelope)
    }

    policy = _object(request["quality_policy"], "request.quality_policy")
    _keys(policy, "request.quality_policy", {"id", "digest"})
    policy_out = {
        "id": _text(policy["id"], "request.quality_policy.id"),
        "digest": _digest(policy["digest"], "request.quality_policy.digest"),
    }

    return {
        "schema_version": 1,
        "capability": capability_out,
        "target": target_out,
        "runtime": runtime_out,
        "representation": representation_out,
        "envelope": envelope_out,
        "quality_policy": policy_out,
    }


def request_digest(request: Any) -> str:
    return sha256_json(normalize_request(request))


def request_identity(request: Any) -> dict[str, Any]:
    normalized = normalize_request(request)
    return {"request": normalized, "request_digest": sha256_json(normalized)}


def _normalize_evidence(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        raise ModelRequestContractError("result.evidence must be an array")
    output: list[dict[str, str]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for index, item in enumerate(value):
        item = _object(item, f"result.evidence[{index}]")
        _keys(item, f"result.evidence[{index}]", {"kind", "digest", "ref", "visibility"})
        normalized = {
            "kind": _text(item["kind"], f"result.evidence[{index}].kind"),
            "digest": _digest(item["digest"], f"result.evidence[{index}].digest"),
            "ref": _text(item["ref"], f"result.evidence[{index}].ref"),
            "visibility": item["visibility"],
        }
        if normalized["visibility"] not in {"public", "private", "local"}:
            raise ModelRequestContractError(f"result.evidence[{index}].visibility is invalid")
        key = tuple(normalized[name] for name in ("kind", "digest", "ref", "visibility"))
        if key in seen:
            raise ModelRequestContractError("result.evidence contains duplicate entries")
        seen.add(key)
        output.append(normalized)
    output.sort(key=lambda item: (item["kind"], item["digest"], item["ref"], item["visibility"]))
    return output


def _normalize_selection(value: Any, request: dict[str, Any]) -> dict[str, Any]:
    selection = _object(value, "result.selection")
    _keys(selection, "result.selection", {"artifact", "representation", "runtime", "target_profile_id"})

    artifact = _object(selection["artifact"], "result.selection.artifact")
    _keys(
        artifact,
        "result.selection.artifact",
        {"provider", "repository", "source_revision"},
    )
    artifact_out = {
        "provider": _text(artifact["provider"], "result.selection.artifact.provider"),
        "repository": _text(artifact["repository"], "result.selection.artifact.repository"),
        "source_revision": _text(artifact["source_revision"], "result.selection.artifact.source_revision"),
    }

    representation = _object(selection["representation"], "result.selection.representation")
    _keys(representation, "result.selection.representation", {"id", "variant", "quantization"})
    representation_out = {
        "id": _text(representation["id"], "result.selection.representation.id"),
        "variant": _text(representation["variant"], "result.selection.representation.variant"),
        "quantization": _text(
            representation["quantization"], "result.selection.representation.quantization"
        ),
    }

    runtime = _object(selection["runtime"], "result.selection.runtime")
    _keys(runtime, "result.selection.runtime", {"id"})
    runtime_out = {"id": _text(runtime["id"], "result.selection.runtime.id")}

    target_profile_id = _text(selection["target_profile_id"], "result.selection.target_profile_id")

    if target_profile_id != request["target"]["profile_id"]:
        raise ModelRequestContractError("result selection target does not match request target")
    if runtime_out["id"] not in request["runtime"]["allowed_ids"]:
        raise ModelRequestContractError("result selection runtime is not allowed by request")
    if representation_out["id"] not in request["representation"]["allowed_ids"]:
        raise ModelRequestContractError("result selection representation is not allowed by request")
    if representation_out["quantization"] not in request["representation"]["allowed_quantizations"]:
        raise ModelRequestContractError("result selection quantization is not allowed by request")

    return {
        "artifact": artifact_out,
        "representation": representation_out,
        "runtime": runtime_out,
        "target_profile_id": target_profile_id,
    }


def _normalize_qualification(value: Any) -> dict[str, str]:
    qualification = _object(value, "result.qualification")
    _keys(qualification, "result.qualification", {"subject_key", "record_digest"})
    return {
        "subject_key": _digest(qualification["subject_key"], "result.qualification.subject_key"),
        "record_digest": _digest(qualification["record_digest"], "result.qualification.record_digest"),
    }


def normalize_result(result: Any, request: Any) -> dict[str, Any]:
    request_norm = normalize_request(request)
    result = _object(result, "result")
    _keys(
        result,
        "result",
        {"schema_version", "request_digest", "status", "reasons", "evidence"},
        {"selection", "qualification"},
    )
    if result["schema_version"] != 1:
        raise ModelRequestContractError("result.schema_version must be 1")
    expected_digest = sha256_json(request_norm)
    if _digest(result["request_digest"], "result.request_digest") != expected_digest:
        raise ModelRequestContractError("result.request_digest does not match canonical request")

    status = result["status"]
    if status not in {"qualified", "candidate", "unknown", "rejected"}:
        raise ModelRequestContractError("result.status is invalid")

    reasons = _sorted_unique_strings(result["reasons"], "result.reasons") if result["reasons"] else []
    evidence = _normalize_evidence(result["evidence"])

    selection = result.get("selection")
    qualification = result.get("qualification")

    output: dict[str, Any] = {
        "schema_version": 1,
        "request_digest": expected_digest,
        "status": status,
        "reasons": reasons,
        "evidence": evidence,
    }

    if status == "qualified":
        if selection is None or qualification is None:
            raise ModelRequestContractError("qualified result requires selection and qualification")
        output["selection"] = _normalize_selection(selection, request_norm)
        output["qualification"] = _normalize_qualification(qualification)
    elif status == "candidate":
        if selection is None:
            raise ModelRequestContractError("candidate result requires selection")
        if qualification is not None:
            raise ModelRequestContractError("candidate result must not contain qualification")
        output["selection"] = _normalize_selection(selection, request_norm)
    else:
        if selection is not None or qualification is not None:
            raise ModelRequestContractError(f"{status} result must not contain selection or qualification")
        if not reasons:
            raise ModelRequestContractError(f"{status} result requires at least one explicit reason")

    return output


def _load(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ModelRequestContractError(f"{path}: top-level value must be an object")
    return value


def _write(path: str | Path, value: dict[str, Any]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".tmp")
    temporary.write_text(canonical_json(value), encoding="utf-8")
    temporary.replace(destination)


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    request_parser = subparsers.add_parser("request")
    request_parser.add_argument("--input", required=True)
    request_parser.add_argument("--output")

    digest_parser = subparsers.add_parser("digest")
    digest_parser.add_argument("--input", required=True)

    result_parser = subparsers.add_parser("result")
    result_parser.add_argument("--request", required=True)
    result_parser.add_argument("--input", required=True)
    result_parser.add_argument("--output")

    args = parser.parse_args()
    if args.command == "request":
        value = normalize_request(_load(args.input))
    elif args.command == "digest":
        print(request_digest(_load(args.input)))
        return 0
    else:
        value = normalize_result(_load(args.input), _load(args.request))

    if args.output:
        _write(args.output, value)
    else:
        print(canonical_json(value), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
