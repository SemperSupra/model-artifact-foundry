from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from provider_adapters.hf_native import (  # noqa: E402
    HuggingFaceCacheMiss,
    HuggingFaceSnapshotVerificationError,
    canonical_json,
    ensure_hf_native_snapshot,
    observation_digest,
)

REVISION = "0123456789abcdef0123456789abcdef01234567"


class FakeCacheMiss(RuntimeError):
    pass


def observation(*, revision=REVISION, files=None):
    return {
        "schema_version": 1,
        "provider": "huggingface",
        "locator": {"repository": "example/tiny-model", "requested_revision": "main"},
        "observed_at": "2026-09-01T00:00:00Z",
        "resolved": {"source_revision": revision, "identity_strength": "repository_commit"},
        "access": {"private": False, "gated": False, "disabled": False},
        "declared_license": {
            "value": "apache-2.0",
            "source": "huggingface-model-card-metadata",
            "interpretation": "declared-metadata-only",
        },
        "files": files if files is not None else [{"path": "config.json", "size": 3}],
        "evidence": {"fixture": "fixture.json", "provenance": "fixture.provenance.json"},
    }


def make_snapshot(tmp_path, content=b"abc"):
    snapshot = tmp_path / "snapshots" / REVISION
    snapshot.mkdir(parents=True)
    (snapshot / "config.json").write_bytes(content)
    return snapshot


def test_cache_hit_is_one_local_only_exact_revision_call(tmp_path):
    snapshot = make_snapshot(tmp_path)
    calls = []

    def download(**kwargs):
        calls.append(kwargs)
        return str(snapshot)

    receipt = ensure_hf_native_snapshot(
        observation(),
        snapshot_download_fn=download,
        cache_miss_exceptions=(FakeCacheMiss,),
    )

    assert calls == [{
        "repo_id": "example/tiny-model",
        "revision": REVISION,
        "local_files_only": True,
    }]
    assert receipt["materialization"]["outcome"] == "cache_hit"
    assert receipt["materialization"]["native_handle"] == str(snapshot.resolve())
    assert receipt["verification"]["files_checked"] == 1
    assert receipt["verification"]["sizes_checked"] == 1


def test_cache_miss_is_explicit_when_network_not_allowed(tmp_path):
    calls = []

    def download(**kwargs):
        calls.append(kwargs)
        raise FakeCacheMiss("not cached")

    with pytest.raises(HuggingFaceCacheMiss, match="not complete in the native cache"):
        ensure_hf_native_snapshot(
            observation(),
            snapshot_download_fn=download,
            cache_miss_exceptions=(FakeCacheMiss,),
        )

    assert len(calls) == 1
    assert calls[0]["local_files_only"] is True


def test_network_materialization_then_repeat_becomes_cache_hit(tmp_path):
    snapshot = make_snapshot(tmp_path)
    calls = []
    cached = False

    def download(**kwargs):
        nonlocal cached
        calls.append(kwargs)
        if kwargs["local_files_only"] and not cached:
            raise FakeCacheMiss("not cached")
        if not kwargs["local_files_only"]:
            cached = True
        return str(snapshot)

    first = ensure_hf_native_snapshot(
        observation(),
        allow_network=True,
        cache_dir=tmp_path / "hf-cache",
        snapshot_download_fn=download,
        cache_miss_exceptions=(FakeCacheMiss,),
    )
    second = ensure_hf_native_snapshot(
        observation(),
        cache_dir=tmp_path / "hf-cache",
        snapshot_download_fn=download,
        cache_miss_exceptions=(FakeCacheMiss,),
    )

    assert [call["local_files_only"] for call in calls] == [True, False, True]
    assert all(call["revision"] == REVISION for call in calls)
    assert all(call["repo_id"] == "example/tiny-model" for call in calls)
    assert first["materialization"]["outcome"] == "materialized"
    assert second["materialization"]["outcome"] == "cache_hit"


def test_receipt_never_contains_credentials_or_invents_model_digest(tmp_path):
    snapshot = make_snapshot(tmp_path)
    calls = []

    def download(**kwargs):
        calls.append(kwargs)
        return str(snapshot)

    receipt = ensure_hf_native_snapshot(
        observation(),
        snapshot_download_fn=download,
        cache_miss_exceptions=(FakeCacheMiss,),
    )
    encoded = canonical_json(receipt)

    assert "token" not in encoded.lower()
    assert "token" not in calls[0]
    assert receipt["verification"]["observation_digest"] == observation_digest(observation())
    assert "content_digest" not in receipt
    assert "model_digest" not in receipt


@pytest.mark.parametrize("path", ["../escape", "/absolute", "folder\\windows-path"])
def test_unsafe_observation_paths_are_rejected_before_provider_call(tmp_path, path):
    calls = []

    def download(**kwargs):
        calls.append(kwargs)
        return str(tmp_path)

    with pytest.raises(ValueError, match="unsafe observation file path"):
        ensure_hf_native_snapshot(
            observation(files=[{"path": path}]),
            snapshot_download_fn=download,
            cache_miss_exceptions=(FakeCacheMiss,),
        )
    assert calls == []


def test_mutable_or_short_revision_is_rejected_before_provider_call():
    calls = []

    def download(**kwargs):
        calls.append(kwargs)
        return "."

    with pytest.raises(ValueError, match="full 40-hex commit"):
        ensure_hf_native_snapshot(
            observation(revision="main"),
            snapshot_download_fn=download,
            cache_miss_exceptions=(FakeCacheMiss,),
        )
    assert calls == []


def test_missing_and_size_mismatched_snapshot_files_fail_verification(tmp_path):
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()

    def missing(**kwargs):
        return str(snapshot)

    with pytest.raises(HuggingFaceSnapshotVerificationError, match="missing expected file"):
        ensure_hf_native_snapshot(
            observation(),
            snapshot_download_fn=missing,
            cache_miss_exceptions=(FakeCacheMiss,),
        )

    (snapshot / "config.json").write_bytes(b"too-long")
    with pytest.raises(HuggingFaceSnapshotVerificationError, match="size mismatch"):
        ensure_hf_native_snapshot(
            observation(),
            snapshot_download_fn=missing,
            cache_miss_exceptions=(FakeCacheMiss,),
        )


def test_canonical_receipt_is_repeatable_for_same_handle_and_outcome(tmp_path):
    snapshot = make_snapshot(tmp_path)

    def download(**kwargs):
        return str(snapshot)

    first = ensure_hf_native_snapshot(
        observation(),
        snapshot_download_fn=download,
        cache_miss_exceptions=(FakeCacheMiss,),
    )
    second = ensure_hf_native_snapshot(
        observation(),
        snapshot_download_fn=download,
        cache_miss_exceptions=(FakeCacheMiss,),
    )
    assert canonical_json(first).encode() == canonical_json(second).encode()


def test_receipt_schema_is_versioned():
    schema = json.loads((ROOT / "schemas/hf-materialization-receipt-v1.schema.json").read_text())
    assert schema["properties"]["schema_version"]["const"] == 1
    assert schema["properties"]["provider"]["const"] == "huggingface"
