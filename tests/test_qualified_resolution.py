from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "qualified_resolution.py"
REQUEST_FIXTURE = ROOT / "fixtures" / "request" / "ui-grounding-request.example.json"
QUALIFICATION_DRAFT = ROOT / "fixtures" / "qualification" / "kv-ground-qualification-draft.example.json"

SPEC = importlib.util.spec_from_file_location("qualified_resolution", TOOL)
assert SPEC is not None and SPEC.loader is not None
RESOLUTION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RESOLUTION)


def request() -> dict:
    return json.loads(REQUEST_FIXTURE.read_text(encoding="utf-8"))


def qualified_receipt(
    *,
    environment_digest: str | None = None,
    recorded_at: str | None = None,
) -> dict:
    draft = json.loads(QUALIFICATION_DRAFT.read_text(encoding="utf-8"))
    req = request()
    digest = RESOLUTION.REQUEST.request_digest(req)
    environment_digest = environment_digest or (
        "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    )
    draft["subject"]["request"]["digest"] = digest
    draft["subject"]["target"]["profile_id"] = req["target"]["profile_id"]
    draft["subject"]["target"]["environment_digest"] = environment_digest
    if recorded_at is not None:
        draft["recorded_at"] = recorded_at
    return RESOLUTION.QUALIFICATION.build_receipt(draft)


def rejected_receipt() -> dict:
    draft = json.loads(QUALIFICATION_DRAFT.read_text(encoding="utf-8"))
    req = request()
    draft["subject"]["request"]["digest"] = RESOLUTION.REQUEST.request_digest(req)
    draft["subject"]["target"]["profile_id"] = req["target"]["profile_id"]
    draft["subject"]["target"]["environment_digest"] = (
        "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    )
    draft["result"]["outcome"] = "rejected"
    draft["result"]["resource_performance"]["status"] = "fail"
    draft["result"]["reasons"] = ["resource envelope failed"]
    return RESOLUTION.QUALIFICATION.build_receipt(draft)


def environment() -> str:
    return "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"


def test_resolution_key_is_stable_for_equivalent_request_environment():
    first = RESOLUTION.resolution_context(request(), environment())
    second_request = copy.deepcopy(request())
    second_request["representation"]["allowed_quantizations"] = ["none", "nf4"]
    second = RESOLUTION.resolution_context(second_request, environment())
    assert first == second
    assert RESOLUTION.resolution_key(first) == RESOLUTION.resolution_key(second)


def test_changed_request_target_or_environment_changes_resolution_key():
    base_request = request()
    base = RESOLUTION.resolution_key(RESOLUTION.resolution_context(base_request, environment()))

    changed_request = copy.deepcopy(base_request)
    changed_request["envelope"]["max_model_load_seconds"] += 1
    assert RESOLUTION.resolution_key(
        RESOLUTION.resolution_context(changed_request, environment())
    ) != base

    changed_target = copy.deepcopy(base_request)
    changed_target["target"]["profile_id"] = "different-target"
    assert RESOLUTION.resolution_key(
        RESOLUTION.resolution_context(changed_target, environment())
    ) != base

    different_environment = (
        "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    )
    assert RESOLUTION.resolution_key(
        RESOLUTION.resolution_context(base_request, different_environment)
    ) != base


def test_binding_is_derived_from_qualified_receipt_and_request():
    receipt = qualified_receipt()
    binding = RESOLUTION.binding_from_qualified_receipt(request(), environment(), receipt)
    assert binding["qualification"]["subject_key"] == receipt["subject_key"]
    assert binding["qualification"]["record_digest"] == receipt["record_digest"]
    assert binding["selection"]["artifact"]["observation_digest"] == (
        receipt["subject"]["artifact"]["observation_digest"]
    )
    assert binding["selection"]["runtime"]["id"] == receipt["subject"]["runtime"]["id"]
    body = {key: value for key, value in binding.items() if key != "binding_digest"}
    assert binding["binding_digest"] == RESOLUTION.sha256_json(body)
    assert RESOLUTION.validate_binding(binding) == binding


def test_rejected_receipt_cannot_create_known_resolution():
    with pytest.raises(RESOLUTION.QualifiedResolutionError, match="only a qualified receipt"):
        RESOLUTION.binding_from_qualified_receipt(request(), environment(), rejected_receipt())


def test_receipt_request_or_environment_mismatch_is_rejected():
    receipt = qualified_receipt()
    changed = request()
    changed["envelope"]["max_model_load_seconds"] += 1
    with pytest.raises(RESOLUTION.QualifiedResolutionError, match="request digest"):
        RESOLUTION.binding_from_qualified_receipt(changed, environment(), receipt)

    with pytest.raises(RESOLUTION.QualifiedResolutionError, match="environment digest"):
        RESOLUTION.binding_from_qualified_receipt(
            request(),
            "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            receipt,
        )


def test_receipt_selection_must_satisfy_request_constraints():
    draft = json.loads(QUALIFICATION_DRAFT.read_text(encoding="utf-8"))
    req = request()
    draft["subject"]["request"]["digest"] = RESOLUTION.REQUEST.request_digest(req)
    draft["subject"]["target"]["profile_id"] = req["target"]["profile_id"]
    draft["subject"]["target"]["environment_digest"] = environment()
    draft["subject"]["representation"]["quantization"] = "q4_k_m"
    receipt = RESOLUTION.QUALIFICATION.build_receipt(draft)
    with pytest.raises(RESOLUTION.QualifiedResolutionError, match="does not satisfy request"):
        RESOLUTION.binding_from_qualified_receipt(req, environment(), receipt)


def test_retain_then_lookup_returns_qualified_result_without_research(tmp_path):
    binding = RESOLUTION.binding_from_qualified_receipt(request(), environment(), qualified_receipt())
    retained = RESOLUTION.retain_binding(tmp_path, binding)
    assert ":" not in retained.name
    assert retained.name == binding["resolution_key"].removeprefix("sha256:") + ".json"

    result = RESOLUTION.lookup(request(), environment(), tmp_path)
    assert result["status"] == "qualified"
    assert result["qualification"] == binding["qualification"]
    assert result["selection"] == binding["selection"]
    assert result["evidence"][0]["kind"] == "retained_resolution_binding"
    assert result["evidence"][0]["digest"] == binding["binding_digest"]


def test_missing_binding_returns_explicit_unknown_without_selection(tmp_path):
    result = RESOLUTION.lookup(request(), environment(), tmp_path)
    assert result["status"] == "unknown"
    assert result["reasons"] == ["no_retained_qualified_resolution"]
    assert "selection" not in result
    assert "qualification" not in result


def test_retain_is_byte_idempotent(tmp_path):
    binding = RESOLUTION.binding_from_qualified_receipt(request(), environment(), qualified_receipt())
    path = RESOLUTION.retain_binding(tmp_path, binding)
    first = path.read_bytes()
    same_path = RESOLUTION.retain_binding(tmp_path, copy.deepcopy(binding))
    assert same_path == path
    assert same_path.read_bytes() == first


def test_new_qualification_event_for_same_resolution_is_explicit_conflict(tmp_path):
    first = RESOLUTION.binding_from_qualified_receipt(
        request(), environment(), qualified_receipt(recorded_at="2026-09-02T00:00:00+00:00")
    )
    second = RESOLUTION.binding_from_qualified_receipt(
        request(), environment(), qualified_receipt(recorded_at="2026-09-03T00:00:00+00:00")
    )
    assert first["resolution_key"] == second["resolution_key"]
    assert first["qualification"]["subject_key"] == second["qualification"]["subject_key"]
    assert first["qualification"]["record_digest"] != second["qualification"]["record_digest"]
    assert first["binding_digest"] != second["binding_digest"]

    RESOLUTION.retain_binding(tmp_path, first)
    with pytest.raises(RESOLUTION.QualifiedResolutionError, match="conflicting retained content"):
        RESOLUTION.retain_binding(tmp_path, second)


def test_tampered_binding_content_fails_closed_instead_of_becoming_unknown(tmp_path):
    binding = RESOLUTION.binding_from_qualified_receipt(request(), environment(), qualified_receipt())
    path = tmp_path / RESOLUTION.binding_filename(binding["resolution_key"])
    tampered = copy.deepcopy(binding)
    tampered["selection"]["artifact"]["repository"] = "attacker/other-model"
    path.write_text(RESOLUTION.canonical_json(tampered), encoding="utf-8")

    with pytest.raises(RESOLUTION.QualifiedResolutionError, match="malformed or tampered"):
        RESOLUTION.lookup(request(), environment(), tmp_path)


def test_tampered_resolution_key_fails_closed(tmp_path):
    binding = RESOLUTION.binding_from_qualified_receipt(request(), environment(), qualified_receipt())
    path = tmp_path / RESOLUTION.binding_filename(binding["resolution_key"])
    tampered = copy.deepcopy(binding)
    tampered["resolution_key"] = (
        "sha256:ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
    )
    path.write_text(RESOLUTION.canonical_json(tampered), encoding="utf-8")

    with pytest.raises(RESOLUTION.QualifiedResolutionError, match="malformed or tampered"):
        RESOLUTION.lookup(request(), environment(), tmp_path)


def test_receipt_event_time_does_not_change_resolution_or_subject_key():
    first = qualified_receipt(recorded_at="2026-09-02T00:00:00+00:00")
    second = qualified_receipt(recorded_at="2026-09-03T01:02:03+00:00")

    assert first["record_digest"] != second["record_digest"]
    first_binding = RESOLUTION.binding_from_qualified_receipt(request(), environment(), first)
    second_binding = RESOLUTION.binding_from_qualified_receipt(request(), environment(), second)
    assert first_binding["resolution_key"] == second_binding["resolution_key"]
    assert first_binding["qualification"]["subject_key"] == second_binding["qualification"]["subject_key"]
