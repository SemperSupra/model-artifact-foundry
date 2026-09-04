from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "model_request_contract.py"
FIXTURE = ROOT / "fixtures" / "request" / "ui-grounding-request.example.json"

SPEC = importlib.util.spec_from_file_location("model_request_contract", TOOL)
assert SPEC is not None and SPEC.loader is not None
CONTRACT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTRACT)


def request() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def selection() -> dict:
    return {
        "artifact": {
            "provider": "huggingface",
            "repository": "vocaela/KV-Ground-8B-BaseGuiOwl1.5-0315",
            "source_revision": "fe7563292bb52ab6c235fc3c87157e6a14017479",
        },
        "representation": {
            "id": "hf-transformers-snapshot",
            "variant": "base",
            "quantization": "nf4",
        },
        "runtime": {"id": "transformers-pytorch"},
        "target_profile_id": "desktop-gpu-target-a",
    }


def result_base(status: str) -> dict:
    return {
        "schema_version": 1,
        "request_digest": CONTRACT.request_digest(request()),
        "status": status,
        "reasons": [],
        "evidence": [],
    }


def test_request_is_byte_canonical_and_array_order_independent():
    first = request()
    second = copy.deepcopy(first)
    second["representation"]["allowed_quantizations"] = ["none", "nf4"]

    first_norm = CONTRACT.normalize_request(first)
    second_norm = CONTRACT.normalize_request(second)

    assert first_norm == second_norm
    assert CONTRACT.canonical_json(first_norm) == CONTRACT.canonical_json(second_norm)
    assert CONTRACT.request_digest(first) == CONTRACT.request_digest(second)


@pytest.mark.parametrize(
    "mutator",
    [
        lambda value: value["target"].update(profile_id="desktop-gpu-target-b"),
        lambda value: value["runtime"].update(offline_required=False),
        lambda value: value["runtime"].update(allowed_ids=["different-runtime"]),
        lambda value: value["representation"].update(allowed_ids=["different-representation"]),
        lambda value: value["representation"].update(allowed_quantizations=["none"]),
        lambda value: value["quality_policy"].update(
            digest="sha256:0000000000000000000000000000000000000000000000000000000000000000"
        ),
        lambda value: value["envelope"].update(max_peak_vram_gib=13),
        lambda value: value["envelope"].update(max_model_load_seconds=121),
        lambda value: value["envelope"].update(max_p95_query_latency_ms=3001),
    ],
)
def test_material_request_changes_change_digest(mutator):
    first = request()
    second = copy.deepcopy(first)
    mutator(second)
    assert CONTRACT.request_digest(first) != CONTRACT.request_digest(second)


def test_optional_envelope_field_presence_is_part_of_identity():
    first = request()
    second = copy.deepcopy(first)
    second["envelope"].pop("max_model_load_seconds")
    assert CONTRACT.request_digest(first) != CONTRACT.request_digest(second)


@pytest.mark.parametrize("forbidden", ["provider", "model", "token", "local_handle", "acquisition"])
def test_provider_model_acquisition_fields_are_rejected(forbidden):
    value = request()
    value[forbidden] = "must-not-be-a-request-field"
    with pytest.raises(CONTRACT.ModelRequestContractError, match="unexpected fields"):
        CONTRACT.normalize_request(value)


def test_invalid_or_duplicate_allowed_values_are_rejected():
    value = request()
    value["runtime"]["allowed_ids"] = ["transformers-pytorch", "transformers-pytorch"]
    with pytest.raises(CONTRACT.ModelRequestContractError, match="duplicates"):
        CONTRACT.normalize_request(value)

    value = request()
    value["envelope"]["max_p95_query_latency_ms"] = 0
    with pytest.raises(CONTRACT.ModelRequestContractError, match="positive finite"):
        CONTRACT.normalize_request(value)


def test_qualified_result_binds_retained_qualification_and_exact_selection():
    value = result_base("qualified")
    value["selection"] = selection()
    value["qualification"] = {
        "subject_key": "sha256:3333333333333333333333333333333333333333333333333333333333333333",
        "record_digest": "sha256:4444444444444444444444444444444444444444444444444444444444444444",
    }
    normalized = CONTRACT.normalize_result(value, request())
    assert normalized["status"] == "qualified"
    assert normalized["selection"]["artifact"]["source_revision"] == selection()["artifact"]["source_revision"]
    assert normalized["qualification"]["subject_key"].startswith("sha256:")


def test_provider_observation_is_evidence_not_selection_identity():
    value = result_base("candidate")
    chosen = selection()
    chosen["artifact"]["observation_digest"] = (
        "sha256:2222222222222222222222222222222222222222222222222222222222222222"
    )
    value["selection"] = chosen
    with pytest.raises(CONTRACT.ModelRequestContractError, match="unexpected fields"):
        CONTRACT.normalize_result(value, request())

    value = result_base("candidate")
    value["selection"] = selection()
    value["evidence"] = [
        {
            "kind": "provider_observation",
            "digest": "sha256:2222222222222222222222222222222222222222222222222222222222222222",
            "ref": "public://foundry/observations/kv-ground.json",
            "visibility": "public",
        }
    ]
    normalized = CONTRACT.normalize_result(value, request())
    assert normalized["selection"] == selection()
    assert normalized["evidence"][0]["kind"] == "provider_observation"


def test_candidate_can_name_exact_selection_but_cannot_claim_qualification():
    value = result_base("candidate")
    value["selection"] = selection()
    normalized = CONTRACT.normalize_result(value, request())
    assert normalized["status"] == "candidate"
    assert "qualification" not in normalized

    value["qualification"] = {
        "subject_key": "sha256:3333333333333333333333333333333333333333333333333333333333333333",
        "record_digest": "sha256:4444444444444444444444444444444444444444444444444444444444444444",
    }
    with pytest.raises(CONTRACT.ModelRequestContractError, match="must not contain qualification"):
        CONTRACT.normalize_result(value, request())


@pytest.mark.parametrize("status", ["unknown", "rejected"])
def test_unknown_and_rejected_require_reason_and_forbid_fake_selection(status):
    value = result_base(status)
    value["reasons"] = ["no retained candidate satisfies the request"]
    normalized = CONTRACT.normalize_result(value, request())
    assert normalized["status"] == status
    assert "selection" not in normalized

    value["selection"] = selection()
    with pytest.raises(CONTRACT.ModelRequestContractError, match="must not contain selection"):
        CONTRACT.normalize_result(value, request())

    value = result_base(status)
    with pytest.raises(CONTRACT.ModelRequestContractError, match="explicit reason"):
        CONTRACT.normalize_result(value, request())


def test_selection_must_satisfy_request_runtime_representation_quantization_and_target():
    value = result_base("candidate")
    chosen = selection()
    chosen["target_profile_id"] = "other-target"
    value["selection"] = chosen
    with pytest.raises(CONTRACT.ModelRequestContractError, match="target"):
        CONTRACT.normalize_result(value, request())

    value = result_base("candidate")
    chosen = selection()
    chosen["runtime"]["id"] = "other-runtime"
    value["selection"] = chosen
    with pytest.raises(CONTRACT.ModelRequestContractError, match="runtime"):
        CONTRACT.normalize_result(value, request())

    value = result_base("candidate")
    chosen = selection()
    chosen["representation"]["id"] = "other-representation"
    value["selection"] = chosen
    with pytest.raises(CONTRACT.ModelRequestContractError, match="representation"):
        CONTRACT.normalize_result(value, request())

    value = result_base("candidate")
    chosen = selection()
    chosen["representation"]["quantization"] = "q4_k_m"
    value["selection"] = chosen
    with pytest.raises(CONTRACT.ModelRequestContractError, match="quantization"):
        CONTRACT.normalize_result(value, request())


def test_result_request_digest_must_match_exact_request():
    value = result_base("unknown")
    value["reasons"] = ["no retained knowledge"]
    value["request_digest"] = "sha256:ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
    with pytest.raises(CONTRACT.ModelRequestContractError, match="does not match"):
        CONTRACT.normalize_result(value, request())


def test_evidence_and_reasons_are_canonicalized_without_changing_semantics():
    value = result_base("rejected")
    value["reasons"] = ["z-reason", "a-reason"]
    value["evidence"] = [
        {
            "kind": "z",
            "digest": "sha256:5555555555555555555555555555555555555555555555555555555555555555",
            "ref": "private://z",
            "visibility": "private",
        },
        {
            "kind": "a",
            "digest": "sha256:6666666666666666666666666666666666666666666666666666666666666666",
            "ref": "public://a",
            "visibility": "public",
        },
    ]
    normalized = CONTRACT.normalize_result(value, request())
    assert normalized["reasons"] == ["a-reason", "z-reason"]
    assert [item["kind"] for item in normalized["evidence"]] == ["a", "z"]
