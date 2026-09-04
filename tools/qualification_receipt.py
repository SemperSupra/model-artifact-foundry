#!/usr/bin/env python3
"""Build and validate deterministic Model Artifact Foundry qualification receipts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class QualificationReceiptError(ValueError):
    """Raised when qualification receipt input violates the v1 contract."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"


def sha256_json(value: Any) -> str:
    digest = hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _require_object(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise QualificationReceiptError(f"{context} must be an object")
    return value


def _require_keys(
    value: dict[str, Any],
    *,
    context: str,
    required: set[str],
    optional: set[str] | None = None,
) -> None:
    optional = optional or set()
    actual = set(value)
    missing = required - actual
    extra = actual - required - optional
    if missing:
        raise QualificationReceiptError(f"{context} missing fields: {', '.join(sorted(missing))}")
    if extra:
        raise QualificationReceiptError(f"{context} has unexpected fields: {', '.join(sorted(extra))}")


def _require_text(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value:
        raise QualificationReceiptError(f"{context} must be a non-empty string")
    return value


def _require_digest(value: Any, context: str) -> str:
    value = _require_text(value, context)
    if _DIGEST_RE.fullmatch(value) is None:
        raise QualificationReceiptError(f"{context} must be sha256:<64 lowercase hex>")
    return value


def _validate_recorded_at(value: Any) -> str:
    value = _require_text(value, "recorded_at")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise QualificationReceiptError("recorded_at must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise QualificationReceiptError("recorded_at must include a timezone")
    return value


def validate_subject(subject: Any) -> dict[str, Any]:
    subject = _require_object(subject, "subject")
    _require_keys(
        subject,
        context="subject",
        required={"capability", "request", "artifact", "representation", "runtime", "target", "validation"},
    )

    capability = _require_object(subject["capability"], "subject.capability")
    _require_keys(capability, context="subject.capability", required={"id", "interface"})
    _require_text(capability["id"], "subject.capability.id")
    _require_text(capability["interface"], "subject.capability.interface")

    request = _require_object(subject["request"], "subject.request")
    _require_keys(request, context="subject.request", required={"digest"})
    _require_digest(request["digest"], "subject.request.digest")

    artifact = _require_object(subject["artifact"], "subject.artifact")
    _require_keys(
        artifact,
        context="subject.artifact",
        required={"provider", "repository", "source_revision", "identity_strength"},
    )
    for key in ("provider", "repository", "source_revision", "identity_strength"):
        _require_text(artifact[key], f"subject.artifact.{key}")

    representation = _require_object(subject["representation"], "subject.representation")
    _require_keys(representation, context="subject.representation", required={"id", "variant", "quantization"})
    for key in ("id", "variant", "quantization"):
        _require_text(representation[key], f"subject.representation.{key}")

    runtime = _require_object(subject["runtime"], "subject.runtime")
    _require_keys(runtime, context="subject.runtime", required={"id", "toolchain_digest", "config_digest"})
    _require_text(runtime["id"], "subject.runtime.id")
    _require_digest(runtime["toolchain_digest"], "subject.runtime.toolchain_digest")
    _require_digest(runtime["config_digest"], "subject.runtime.config_digest")

    target = _require_object(subject["target"], "subject.target")
    _require_keys(target, context="subject.target", required={"profile_id", "environment_digest"})
    _require_text(target["profile_id"], "subject.target.profile_id")
    _require_digest(target["environment_digest"], "subject.target.environment_digest")

    validation = _require_object(subject["validation"], "subject.validation")
    _require_keys(
        validation,
        context="subject.validation",
        required={"project", "workload_id", "holdout_digest", "evaluator_digest", "policy_digest"},
        optional={"capture_manifest_digest"},
    )
    _require_text(validation["project"], "subject.validation.project")
    _require_text(validation["workload_id"], "subject.validation.workload_id")
    for key in ("holdout_digest", "evaluator_digest", "policy_digest"):
        _require_digest(validation[key], f"subject.validation.{key}")
    if "capture_manifest_digest" in validation:
        _require_digest(validation["capture_manifest_digest"], "subject.validation.capture_manifest_digest")

    return subject


def validate_result(result: Any) -> dict[str, Any]:
    result = _require_object(result, "result")
    _require_keys(result, context="result", required={"outcome", "quality", "resource_performance", "reasons"})
    if result["outcome"] not in {"qualified", "rejected"}:
        raise QualificationReceiptError("result.outcome must be qualified or rejected")

    statuses: list[str] = []
    for gate_name in ("quality", "resource_performance"):
        gate = _require_object(result[gate_name], f"result.{gate_name}")
        _require_keys(gate, context=f"result.{gate_name}", required={"status", "result_digest"})
        if gate["status"] not in {"pass", "fail"}:
            raise QualificationReceiptError(f"result.{gate_name}.status must be pass or fail")
        statuses.append(gate["status"])
        _require_digest(gate["result_digest"], f"result.{gate_name}.result_digest")

    reasons = result["reasons"]
    if not isinstance(reasons, list) or any(not isinstance(item, str) or not item for item in reasons):
        raise QualificationReceiptError("result.reasons must be an array of non-empty strings")
    if len(set(reasons)) != len(reasons):
        raise QualificationReceiptError("result.reasons must be unique")

    if result["outcome"] == "qualified":
        if statuses != ["pass", "pass"]:
            raise QualificationReceiptError("qualified requires quality and resource_performance to pass")
        if reasons:
            raise QualificationReceiptError("qualified result must not contain rejection reasons")
    else:
        if "fail" not in statuses:
            raise QualificationReceiptError("rejected requires at least one failed gate")
        if not reasons:
            raise QualificationReceiptError("rejected result requires at least one reason")

    return result


def normalize_evidence(evidence: Any) -> list[dict[str, Any]]:
    if not isinstance(evidence, list):
        raise QualificationReceiptError("evidence must be an array")
    normalized: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for index, item in enumerate(evidence):
        item = _require_object(item, f"evidence[{index}]")
        _require_keys(item, context=f"evidence[{index}]", required={"kind", "digest", "ref", "visibility"})
        kind = _require_text(item["kind"], f"evidence[{index}].kind")
        digest = _require_digest(item["digest"], f"evidence[{index}].digest")
        ref = _require_text(item["ref"], f"evidence[{index}].ref")
        visibility = item["visibility"]
        if visibility not in {"public", "private", "local"}:
            raise QualificationReceiptError(f"evidence[{index}].visibility is invalid")
        key = (kind, digest, ref, visibility)
        if key in seen:
            raise QualificationReceiptError("duplicate evidence entry")
        seen.add(key)
        normalized.append({"kind": kind, "digest": digest, "ref": ref, "visibility": visibility})
    normalized.sort(key=lambda item: (item["kind"], item["digest"], item["ref"], item["visibility"]))
    return normalized


def build_receipt(draft: Any) -> dict[str, Any]:
    draft = _require_object(draft, "draft")
    _require_keys(draft, context="draft", required={"schema_version", "recorded_at", "subject", "result", "evidence"})
    if draft["schema_version"] != 1:
        raise QualificationReceiptError("schema_version must be 1")

    recorded_at = _validate_recorded_at(draft["recorded_at"])
    subject = validate_subject(draft["subject"])
    result = validate_result(draft["result"])
    evidence = normalize_evidence(draft["evidence"])

    receipt: dict[str, Any] = {
        "schema_version": 1,
        "recorded_at": recorded_at,
        "subject": subject,
        "subject_key": sha256_json(subject),
        "result": result,
        "evidence": evidence,
    }
    receipt["record_digest"] = sha256_json(receipt)
    return receipt


def validate_receipt(receipt: Any) -> dict[str, Any]:
    receipt = _require_object(receipt, "receipt")
    _require_keys(
        receipt,
        context="receipt",
        required={"schema_version", "recorded_at", "subject", "subject_key", "result", "evidence", "record_digest"},
    )
    if receipt["schema_version"] != 1:
        raise QualificationReceiptError("schema_version must be 1")
    _validate_recorded_at(receipt["recorded_at"])
    subject = validate_subject(receipt["subject"])
    validate_result(receipt["result"])
    normalized_evidence = normalize_evidence(receipt["evidence"])
    if normalized_evidence != receipt["evidence"]:
        raise QualificationReceiptError("evidence must be in canonical sorted order")

    expected_subject_key = sha256_json(subject)
    if receipt["subject_key"] != expected_subject_key:
        raise QualificationReceiptError("subject_key does not match canonical subject")
    _require_digest(receipt["record_digest"], "record_digest")
    digest_basis = {key: value for key, value in receipt.items() if key != "record_digest"}
    expected_record_digest = sha256_json(digest_basis)
    if receipt["record_digest"] != expected_record_digest:
        raise QualificationReceiptError("record_digest does not match canonical receipt body")
    return receipt


def _load(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise QualificationReceiptError("input must contain a JSON object")
    return value


def _write(path: str | Path, value: dict[str, Any]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".tmp")
    temporary.write_text(canonical_json(value), encoding="utf-8")
    temporary.replace(destination)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output")
    parser.add_argument("--validate-existing", action="store_true")
    args = parser.parse_args()

    value = _load(args.input)
    if args.validate_existing:
        receipt = validate_receipt(value)
    else:
        receipt = build_receipt(value)

    if args.output:
        _write(args.output, receipt)
    else:
        print(canonical_json(receipt), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
