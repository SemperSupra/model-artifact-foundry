from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "qualification_receipt.py"
FIXTURE = ROOT / "fixtures" / "qualification" / "kv-ground-qualification-draft.example.json"
SCHEMA = ROOT / "schemas" / "qualification-receipt-v1.schema.json"

SPEC = importlib.util.spec_from_file_location("qualification_receipt", TOOL)
assert SPEC is not None and SPEC.loader is not None
RECEIPT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RECEIPT)


def load_draft() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_build_is_byte_repeatable_and_self_validating():
    first = RECEIPT.build_receipt(load_draft())
    second = RECEIPT.build_receipt(load_draft())
    assert RECEIPT.canonical_json(first) == RECEIPT.canonical_json(second)
    assert first["subject_key"].startswith("sha256:")
    assert first["record_digest"].startswith("sha256:")
    assert RECEIPT.validate_receipt(first) == first


def test_event_time_changes_record_but_not_subject_key():
    first_draft = load_draft()
    second_draft = load_draft()
    second_draft["recorded_at"] = "2026-09-02T00:01:00+00:00"

    first = RECEIPT.build_receipt(first_draft)
    second = RECEIPT.build_receipt(second_draft)

    assert first["subject_key"] == second["subject_key"]
    assert first["record_digest"] != second["record_digest"]


def test_evidence_order_is_canonical_and_does_not_change_record():
    first_draft = load_draft()
    second_draft = load_draft()
    second_draft["evidence"] = list(reversed(second_draft["evidence"]))

    first = RECEIPT.build_receipt(first_draft)
    second = RECEIPT.build_receipt(second_draft)

    assert first == second
    assert first["evidence"] == sorted(
        first["evidence"],
        key=lambda item: (item["kind"], item["digest"], item["ref"], item["visibility"]),
    )


def test_machine_local_materialization_receipt_changes_record_not_subject():
    first_draft = load_draft()
    second_draft = load_draft()
    item = next(e for e in second_draft["evidence"] if e["kind"] == "materialization_receipt")
    item["digest"] = "sha256:dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"
    item["ref"] = "local://another-machine/materialization-receipt.json"

    first = RECEIPT.build_receipt(first_draft)
    second = RECEIPT.build_receipt(second_draft)

    assert first["subject_key"] == second["subject_key"]
    assert first["record_digest"] != second["record_digest"]


def test_provider_observation_recapture_changes_record_not_subject():
    first_draft = load_draft()
    second_draft = load_draft()
    item = next(e for e in second_draft["evidence"] if e["kind"] == "provider_observation")
    item["digest"] = "sha256:eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
    item["ref"] = "public://foundry/observations/kv-ground-recaptured.json"

    first = RECEIPT.build_receipt(first_draft)
    second = RECEIPT.build_receipt(second_draft)

    assert first["subject_key"] == second["subject_key"]
    assert first["record_digest"] != second["record_digest"]


@pytest.mark.parametrize(
    ("path", "replacement"),
    [
        (("request", "digest"), "sha256:0000000000000000000000000000000000000000000000000000000000000000"),
        (("artifact", "source_revision"), "0123456789abcdef0123456789abcdef01234567"),
        (("representation", "quantization"), "none"),
        (("runtime", "toolchain_digest"), "sha256:0000000000000000000000000000000000000000000000000000000000000000"),
        (("target", "environment_digest"), "sha256:0000000000000000000000000000000000000000000000000000000000000000"),
        (("validation", "holdout_digest"), "sha256:0000000000000000000000000000000000000000000000000000000000000000"),
        (("validation", "policy_digest"), "sha256:0000000000000000000000000000000000000000000000000000000000000000"),
    ],
)
def test_material_subject_changes_change_lookup_key(path, replacement):
    first_draft = load_draft()
    second_draft = copy.deepcopy(first_draft)
    second_draft["subject"][path[0]][path[1]] = replacement

    first = RECEIPT.build_receipt(first_draft)
    second = RECEIPT.build_receipt(second_draft)

    assert first["subject_key"] != second["subject_key"]


def test_qualified_requires_both_independent_gates_to_pass():
    draft = load_draft()
    draft["result"]["resource_performance"]["status"] = "fail"
    draft["result"]["resource_performance"]["result_digest"] = (
        "sha256:eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
    )
    with pytest.raises(RECEIPT.QualificationReceiptError, match="qualified requires"):
        RECEIPT.build_receipt(draft)


def test_rejected_requires_failed_gate_and_explicit_reason():
    draft = load_draft()
    draft["result"]["outcome"] = "rejected"
    draft["result"]["quality"]["status"] = "fail"
    draft["result"]["reasons"] = ["quality threshold failed"]
    receipt = RECEIPT.build_receipt(draft)
    assert receipt["result"]["outcome"] == "rejected"

    invalid = load_draft()
    invalid["result"]["outcome"] = "rejected"
    with pytest.raises(RECEIPT.QualificationReceiptError, match="requires at least one failed gate"):
        RECEIPT.build_receipt(invalid)


def test_unknown_is_not_a_qualification_receipt_outcome():
    draft = load_draft()
    draft["result"]["outcome"] = "unknown"
    with pytest.raises(RECEIPT.QualificationReceiptError, match="qualified or rejected"):
        RECEIPT.build_receipt(draft)


def test_tampering_with_subject_or_record_digest_is_detected():
    receipt = RECEIPT.build_receipt(load_draft())
    tampered = copy.deepcopy(receipt)
    tampered["subject"]["target"]["profile_id"] = "different-target"
    with pytest.raises(RECEIPT.QualificationReceiptError, match="subject_key"):
        RECEIPT.validate_receipt(tampered)

    tampered = copy.deepcopy(receipt)
    tampered["recorded_at"] = "2026-09-02T00:02:00+00:00"
    with pytest.raises(RECEIPT.QualificationReceiptError, match="record_digest"):
        RECEIPT.validate_receipt(tampered)


def test_schema_keeps_event_local_identity_out_of_subject():
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    subject_text = json.dumps(schema["$defs"]["subject"], sort_keys=True)
    assert "native_handle" not in subject_text
    assert "materialization_receipt_digest" not in subject_text
    assert "observation_digest" not in subject_text
    assert schema["$defs"]["result"]["properties"]["outcome"]["enum"] == ["qualified", "rejected"]
