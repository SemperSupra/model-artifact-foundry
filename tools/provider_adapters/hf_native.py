"""Hugging Face provider-native snapshot materialization for the first MVP slice.

This module is intentionally provider-specific. It consumes an already-normalized
exact Hugging Face observation, uses the provider-native cache, and returns a
machine-local handle plus a small receipt. It is not a generic plugin/materializer
framework and it does not own runtime loading or project qualification.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterable

SHA1_RE = re.compile(r"^[0-9a-f]{40}$")


class HuggingFaceCacheMiss(RuntimeError):
    """The requested exact snapshot is not complete in the native cache."""


class HuggingFaceSnapshotVerificationError(RuntimeError):
    """The returned provider-native snapshot does not match expected structure."""


def canonical_json(value: Any) -> str:
    """Return canonical JSON used for stable evidence digests."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"


def observation_digest(observation: dict[str, Any]) -> str:
    """Digest the normalized observation, not the model bytes."""
    digest = hashlib.sha256(canonical_json(observation).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _safe_relative_path(value: Any) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError(f"unsafe observation file path: {value!r}")
    path = PurePosixPath(value)
    if path.as_posix() != value or path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise ValueError(f"unsafe observation file path: {value!r}")
    return path


def _observation_fields(
    observation: dict[str, Any],
) -> tuple[str, str, str, list[dict[str, Any]]]:
    if observation.get("provider") != "huggingface":
        raise ValueError("observation provider must be huggingface")

    locator = observation.get("locator") or {}
    repository = locator.get("repository")
    if not isinstance(repository, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*", repository) or any(part in (".", "..") for part in repository.split("/")):
        raise ValueError("observation locator.repository must be an exact owner/repository")

    resolved = observation.get("resolved") or {}
    revision = resolved.get("source_revision")
    if not isinstance(revision, str) or not SHA1_RE.fullmatch(revision):
        raise ValueError("observation resolved.source_revision must be a full 40-hex commit")
    identity_strength = resolved.get("identity_strength")
    if identity_strength != "repository_commit":
        raise ValueError("observation identity_strength must be repository_commit")

    files = observation.get("files")
    if not isinstance(files, list):
        raise ValueError("observation files must be a list")

    seen: set[str] = set()
    normalized_files: list[dict[str, Any]] = []
    for item in files:
        if not isinstance(item, dict):
            raise ValueError("each observation file must be an object")
        rel = _safe_relative_path(item.get("path"))
        rel_text = rel.as_posix()
        if rel_text in seen:
            raise ValueError(f"duplicate observation file path: {rel_text}")
        seen.add(rel_text)
        if "size" in item and (not isinstance(item["size"], int) or item["size"] < 0):
            raise ValueError(f"invalid observation size for {rel_text}")
        normalized_files.append(item)

    return repository, revision, identity_strength, normalized_files


def verify_native_snapshot(
    snapshot_path: str | Path,
    files: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Verify expected paths/sizes without re-hashing multi-GB model payloads.

    Hugging Face snapshots may contain symlinks into the provider-native blob
    cache, so verification deliberately checks safe relative names plus the
    resulting file/size and bounding symlinks to the same provider-native
    model/blob cache instead of following arbitrary host paths.
    """
    root = Path(snapshot_path)
    if not root.exists() or not root.is_dir() or root.is_symlink():
        raise HuggingFaceSnapshotVerificationError(
            "native snapshot handle must be a real existing directory"
        )
    root_real = root.resolve(strict=True)
    # Native Hub file symlinks point to blobs in the same model cache (or
    # its provider-owned shared blob directory), not arbitrary host paths.
    if root_real.parent.name == "snapshots":
        model_cache = root_real.parent.parent
        allowed_blobs = (model_cache / "blobs", model_cache.parent / "blobs")
    else:
        allowed_blobs = ()

    def within(child: Path, parent: Path) -> bool:
        return child == parent or parent in child.parents

    checked = 0
    sizes_checked = 0
    for item in files:
        rel = _safe_relative_path(item.get("path"))
        candidate = root.joinpath(*rel.parts)
        for ancestor in candidate.parents:
            if ancestor == root:
                break
            if ancestor.is_symlink():
                raise HuggingFaceSnapshotVerificationError(
                    f"snapshot ancestor symlink is not permitted: {rel.as_posix()}"
                )
        if not candidate.exists() or not candidate.is_file():
            raise HuggingFaceSnapshotVerificationError(
                f"snapshot missing expected file: {rel.as_posix()}"
            )
        target = candidate.resolve(strict=True)
        if candidate.is_symlink():
            if not any(within(target, parent) for parent in allowed_blobs):
                raise HuggingFaceSnapshotVerificationError(
                    f"snapshot link escapes provider-native blob cache: {rel.as_posix()}"
                )
        elif not within(target, root_real):
            raise HuggingFaceSnapshotVerificationError(
                f"snapshot path escapes snapshot root: {rel.as_posix()}"
            )
        if target.stat().st_nlink != 1:
            raise HuggingFaceSnapshotVerificationError(
                f"snapshot hardlink needs separate custody verification: {rel.as_posix()}"
            )
        checked += 1
        if "size" in item:
            actual_size = target.stat().st_size
            if actual_size != item["size"]:
                raise HuggingFaceSnapshotVerificationError(
                    f"snapshot size mismatch for {rel.as_posix()}: "
                    f"expected {item['size']}, got {actual_size}"
                )
            sizes_checked += 1

    return {
        "status": "verified_structure",
        "files_checked": checked,
        "sizes_checked": sizes_checked,
    }


def _real_snapshot_download() -> tuple[Callable[..., str], tuple[type[BaseException], ...]]:
    from huggingface_hub import snapshot_download
    from huggingface_hub.errors import LocalEntryNotFoundError

    return snapshot_download, (LocalEntryNotFoundError,)


def ensure_hf_native_snapshot(
    observation: dict[str, Any],
    *,
    allow_network: bool = False,
    cache_dir: str | Path | None = None,
    snapshot_download_fn: Callable[..., str] | None = None,
    cache_miss_exceptions: tuple[type[BaseException], ...] | None = None,
) -> dict[str, Any]:
    """Ensure an exact HF revision in the native cache and return a verified handle.

    The first attempt is always cache-only. Network acquisition occurs only after
    a recognized cache miss and only when ``allow_network`` is explicitly true.
    No token value is accepted or emitted by this API; the real Hugging Face client
    may use its native credential resolution at this acquisition boundary.
    """
    repository, revision, identity_strength, files = _observation_fields(observation)

    if snapshot_download_fn is None:
        snapshot_download_fn, default_miss = _real_snapshot_download()
        if cache_miss_exceptions is None:
            cache_miss_exceptions = default_miss
    if cache_miss_exceptions is None:
        cache_miss_exceptions = (HuggingFaceCacheMiss,)

    kwargs: dict[str, Any] = {
        "repo_id": repository,
        "revision": revision,
        "local_files_only": True,
    }
    if cache_dir is not None:
        kwargs["cache_dir"] = str(cache_dir)

    try:
        handle = snapshot_download_fn(**kwargs)
        outcome = "cache_hit"
    except cache_miss_exceptions as exc:
        if not allow_network:
            raise HuggingFaceCacheMiss(
                f"exact Hugging Face snapshot {repository}@{revision} "
                "is not complete in the native cache"
            ) from exc
        network_kwargs = dict(kwargs)
        network_kwargs["local_files_only"] = False
        handle = snapshot_download_fn(**network_kwargs)
        outcome = "materialized"

    verification = verify_native_snapshot(handle, files)
    native_handle = str(Path(handle).resolve())
    return {
        "schema_version": 1,
        "provider": "huggingface",
        "repository": repository,
        "source_revision": revision,
        "identity_strength": identity_strength,
        "materialization": {
            "handle_kind": "huggingface_native_snapshot",
            "native_handle": native_handle,
            "outcome": outcome,
            "provider_native_cache": True,
        },
        "verification": {
            **verification,
            "observation_digest": observation_digest(observation),
        },
    }
