#!/usr/bin/env python3
"""Check first-consumer MVP evidence readiness without making the authority decision."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class DecisionEvidenceError(ValueError):
    """Raised when the decision-evidence manifest violates the v1 contract."""


def _object(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DecisionEvidenceError(f"{context} must be an object")
    return value


def _keys(value: dict[str, Any], context: str, required: set[str]) -> None:
    actual = set(value)
    missing = required - actual
    extra = actual - required
    if missing:
        raise DecisionEvidenceError(f"{context} missing fields: {', '.join(sorted(missing))}")
    if extra:
        raise DecisionEvidenceError(f"{context} has unexpected fields: {', '.join(sorted(extra))}")


def _text(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value:
        raise DecisionEvidenceError(f"{context} must be a non-empty string")
    return value


def _digest(value: Any, context: str) -> str:
    value = _text(value, context)
    if _DIGEST_RE.fullmatch(value) is None:
        raise DecisionEvidenceError(f"{context} must be sha256:<64 lowercase hex>")
    return value


def _boolean(value: Any, context: str) -> bool:
    if not isinstance(value, bool):
        raise DecisionEvidenceError(f"{context} must be boolean")
    return value


def validate_manifest(manifest: Any) -> dict[str, Any]:
    manifest = _object(manifest, "manifest")
    _keys(
        manifest,
        "manifest",
        {
            "schema_version",
            "gate_id",
            "recorded_at",
            "qualification",
            "equivalent_repeat",
            "changed_envelope",
            "consumer_delta",
            "control_r4",
            "lifecycle",
        },
    )
    if manifest["schema_version"] != 1:
        raise DecisionEvidenceError("schema_version must be 1")
    _text(manifest["gate_id"], "gate_id")
    recorded_at = _text(manifest["recorded_at"], "recorded_at")
    try:
        parsed = datetime.fromisoformat(recorded_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DecisionEvidenceError("recorded_at must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise DecisionEvidenceError("recorded_at must include a timezone")

    qualification = _object(manifest["qualification"], "qualification")
    _keys(qualification, "qualification", {"receipt_digest", "subject_key", "outcome"})
    _digest(qualification["receipt_digest"], "qualification.receipt_digest")
    _digest(qualification["subject_key"], "qualification.subject_key")
    if qualification["outcome"] not in {"qualified", "rejected"}:
        raise DecisionEvidenceError("qualification.outcome must be qualified or rejected")

    repeat = _object(manifest["equivalent_repeat"], "equivalent_repeat")
    _keys(
        repeat,
        "equivalent_repeat",
        {
            "attempted",
            "repeated_subject_key",
            "deterministic_record_lookup",
            "generator_invoked",
            "provider_research_invoked",
            "evidence_digest",
        },
    )
    for key in ("attempted", "deterministic_record_lookup", "generator_invoked", "provider_research_invoked"):
        _boolean(repeat[key], f"equivalent_repeat.{key}")
    _digest(repeat["repeated_subject_key"], "equivalent_repeat.repeated_subject_key")
    _digest(repeat["evidence_digest"], "equivalent_repeat.evidence_digest")

    changed = _object(manifest["changed_envelope"], "changed_envelope")
    _keys(
        changed,
        "changed_envelope",
        {
            "attempted",
            "changed_dimension",
            "original_request_digest",
            "changed_request_digest",
            "old_record_reused",
            "deterministic_disposition",
            "generator_invoked",
            "evidence_digest",
        },
    )
    for key in ("attempted", "old_record_reused", "generator_invoked"):
        _boolean(changed[key], f"changed_envelope.{key}")
    _text(changed["changed_dimension"], "changed_envelope.changed_dimension")
    _digest(changed["original_request_digest"], "changed_envelope.original_request_digest")
    _digest(changed["changed_request_digest"], "changed_envelope.changed_request_digest")
    _digest(changed["evidence_digest"], "changed_envelope.evidence_digest")
    if changed["deterministic_disposition"] not in {"known_qualified_alternative", "unknown", "rejected"}:
        raise DecisionEvidenceError("changed_envelope.deterministic_disposition is invalid")

    consumer = _object(manifest["consumer_delta"], "consumer_delta")
    consumer_bools = {
        "exact_identity_preserved",
        "verified_local_handle_normal_path",
        "provider_credentials_removed_from_normal_serving",
        "implicit_provider_download_not_normal_path",
        "provider_native_storage_preserved",
        "repeated_research_avoided",
    }
    _keys(consumer, "consumer_delta", consumer_bools | {"evidence_digest"})
    for key in consumer_bools:
        _boolean(consumer[key], f"consumer_delta.{key}")
    _digest(consumer["evidence_digest"], "consumer_delta.evidence_digest")

    control = _object(manifest["control_r4"], "control_r4")
    control_bools = {
        "validator_policy_frozen_before_results",
        "holdout_frozen_before_results",
        "exact_evidence_retained",
        "repeat_idempotent",
        "rollback_understood",
        "privacy_preserved",
    }
    _keys(control, "control_r4", control_bools | {"evidence_digest"})
    for key in control_bools:
        _boolean(control[key], f"control_r4.{key}")
    _digest(control["evidence_digest"], "control_r4.evidence_digest")

    lifecycle = _object(manifest["lifecycle"], "lifecycle")
    _keys(lifecycle, "lifecycle", {"assessment_digest", "assessment_ref"})
    _digest(lifecycle["assessment_digest"], "lifecycle.assessment_digest")
    _text(lifecycle["assessment_ref"], "lifecycle.assessment_ref")

    return manifest


def evaluate_readiness(manifest: Any) -> dict[str, Any]:
    manifest = validate_manifest(manifest)
    qualification = manifest["qualification"]
    repeat = manifest["equivalent_repeat"]
    changed = manifest["changed_envelope"]
    consumer = manifest["consumer_delta"]
    control = manifest["control_r4"]

    readiness_blockers: list[str] = []
    if not repeat["attempted"]:
        readiness_blockers.append("equivalent repeat has not been attempted")
    if not changed["attempted"]:
        readiness_blockers.append("changed-envelope test has not been attempted")
    if changed["original_request_digest"] == changed["changed_request_digest"]:
        readiness_blockers.append("changed-envelope test did not change the request digest")

    for key, label in (
        ("validator_policy_frozen_before_results", "validator policy was not frozen before results"),
        ("holdout_frozen_before_results", "holdout was not frozen before results"),
        ("exact_evidence_retained", "exact evidence was not retained"),
        ("privacy_preserved", "privacy boundary was not preserved"),
    ):
        if not control[key]:
            readiness_blockers.append(label)

    go_blockers = list(readiness_blockers)
    if qualification["outcome"] != "qualified":
        go_blockers.append("first-consumer qualification outcome is not qualified")
    if repeat["repeated_subject_key"] != qualification["subject_key"]:
        go_blockers.append("equivalent repeat did not reproduce the qualification subject key")
    if not repeat["deterministic_record_lookup"]:
        go_blockers.append("equivalent repeat did not resolve through deterministic retained-record lookup")
    if repeat["generator_invoked"]:
        go_blockers.append("generator was invoked for an equivalent retained subject")
    if repeat["provider_research_invoked"]:
        go_blockers.append("provider/model research was invoked for an equivalent retained subject")
    if changed["old_record_reused"]:
        go_blockers.append("changed envelope incorrectly reused the old qualification record")
    if changed["generator_invoked"] and changed["deterministic_disposition"] != "unknown":
        go_blockers.append("generator was invoked without an UNKNOWN changed-envelope disposition")

    for key, label in (
        ("exact_identity_preserved", "exact identity was not preserved"),
        ("verified_local_handle_normal_path", "verified local handle is not the normal qualified path"),
        ("provider_credentials_removed_from_normal_serving", "provider credentials remain in normal serving"),
        ("implicit_provider_download_not_normal_path", "implicit provider download remains the normal path"),
        ("provider_native_storage_preserved", "provider-native storage ownership was not preserved"),
        ("repeated_research_avoided", "repeat evidence does not show avoided research/acquisition work"),
    ):
        if not consumer[key]:
            go_blockers.append(label)

    if not control["repeat_idempotent"]:
        go_blockers.append("repeat/idempotence requirement failed")
    if not control["rollback_understood"]:
        go_blockers.append("rollback path is not understood")

    return {
        "schema_version": 1,
        "gate_id": manifest["gate_id"],
        "decision_readiness": "READY" if not readiness_blockers else "NOT_READY",
        "readiness_blockers": sorted(set(readiness_blockers)),
        "go_mechanical_eligible": not go_blockers,
        "go_blockers": sorted(set(go_blockers)),
        "authority_note": "This checker does not choose GO, NARROW, or KILL.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()

    with Path(args.input).open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    result = evaluate_readiness(manifest)
    rendered = json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if result["decision_readiness"] == "READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
