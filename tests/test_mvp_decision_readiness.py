from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "check_mvp_decision_readiness.py"
FIXTURE = ROOT / "fixtures" / "decision" / "first-consumer-ready.example.json"
SCHEMA = ROOT / "schemas" / "mvp-decision-evidence-v1.schema.json"

SPEC = importlib.util.spec_from_file_location("check_mvp_decision_readiness", TOOL)
assert SPEC is not None and SPEC.loader is not None
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)


def load_manifest() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_complete_successful_fixture_is_ready_and_go_mechanically_eligible():
    result = CHECK.evaluate_readiness(load_manifest())
    assert result["decision_readiness"] == "READY"
    assert result["readiness_blockers"] == []
    assert result["go_mechanical_eligible"] is True
    assert result["go_blockers"] == []
    assert "GO" in result["authority_note"]
    assert "decision" not in result


def test_rejected_qualification_can_be_decision_ready_but_never_go_eligible():
    manifest = load_manifest()
    manifest["qualification"]["outcome"] = "rejected"
    result = CHECK.evaluate_readiness(manifest)
    assert result["decision_readiness"] == "READY"
    assert result["go_mechanical_eligible"] is False
    assert any("not qualified" in item for item in result["go_blockers"])


def test_failed_deterministic_repeat_is_evidence_not_missing_evidence():
    manifest = load_manifest()
    manifest["equivalent_repeat"]["deterministic_record_lookup"] = False
    manifest["equivalent_repeat"]["generator_invoked"] = True
    result = CHECK.evaluate_readiness(manifest)
    assert result["decision_readiness"] == "READY"
    assert result["go_mechanical_eligible"] is False
    assert any("deterministic retained-record lookup" in item for item in result["go_blockers"])
    assert any("generator was invoked" in item for item in result["go_blockers"])


def test_unattempted_required_experiment_is_not_ready():
    manifest = load_manifest()
    manifest["equivalent_repeat"]["attempted"] = False
    result = CHECK.evaluate_readiness(manifest)
    assert result["decision_readiness"] == "NOT_READY"
    assert any("has not been attempted" in item for item in result["readiness_blockers"])


def test_changed_envelope_must_actually_change_request_identity():
    manifest = load_manifest()
    manifest["changed_envelope"]["changed_request_digest"] = manifest["changed_envelope"]["original_request_digest"]
    result = CHECK.evaluate_readiness(manifest)
    assert result["decision_readiness"] == "NOT_READY"
    assert any("did not change the request digest" in item for item in result["readiness_blockers"])


def test_generator_escalation_is_allowed_only_from_unknown_for_go_eligibility():
    manifest = load_manifest()
    manifest["changed_envelope"]["deterministic_disposition"] = "known_qualified_alternative"
    manifest["changed_envelope"]["generator_invoked"] = True
    result = CHECK.evaluate_readiness(manifest)
    assert result["decision_readiness"] == "READY"
    assert result["go_mechanical_eligible"] is False
    assert any("without an UNKNOWN" in item for item in result["go_blockers"])


def test_contaminated_or_unretained_evidence_blocks_decision_readiness():
    for field in (
        "validator_policy_frozen_before_results",
        "holdout_frozen_before_results",
        "exact_evidence_retained",
        "privacy_preserved",
    ):
        manifest = load_manifest()
        manifest["control_r4"][field] = False
        result = CHECK.evaluate_readiness(manifest)
        assert result["decision_readiness"] == "NOT_READY", field


def test_consumer_value_failures_are_go_blockers_but_still_decision_evidence():
    manifest = load_manifest()
    manifest["consumer_delta"]["repeated_research_avoided"] = False
    result = CHECK.evaluate_readiness(manifest)
    assert result["decision_readiness"] == "READY"
    assert result["go_mechanical_eligible"] is False
    assert any("avoided research" in item for item in result["go_blockers"])


def test_subject_key_mismatch_on_equivalent_repeat_blocks_go():
    manifest = load_manifest()
    manifest["equivalent_repeat"]["repeated_subject_key"] = (
        "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    )
    result = CHECK.evaluate_readiness(manifest)
    assert result["decision_readiness"] == "READY"
    assert result["go_mechanical_eligible"] is False
    assert any("subject key" in item for item in result["go_blockers"])


def test_invalid_digest_is_rejected_as_contract_error():
    manifest = load_manifest()
    manifest["qualification"]["receipt_digest"] = "not-a-digest"
    with pytest.raises(CHECK.DecisionEvidenceError, match="sha256"):
        CHECK.evaluate_readiness(manifest)


def test_schema_contains_evidence_only_and_no_authority_decision_field():
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    properties = schema["properties"]
    assert "decision" not in properties
    assert "go_narrow_kill" not in json.dumps(schema).lower()
